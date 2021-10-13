"""Docker container management for tierkreis runtime servers and workers."""

import os
import socket
import subprocess
import sys
from contextlib import AbstractAsyncContextManager, ExitStack, contextmanager
from pathlib import Path
from types import TracebackType
from typing import (
    IO,
    TYPE_CHECKING,
    Callable,
    Iterator,
    List,
    Optional,
    Type,
    Union,
    cast,
)

from grpclib.client import Channel

from docker import DockerClient  # type: ignore

from .runtime_client import RuntimeClient, RuntimeLaunchFailed
from .myqos_client import _get_myqos_creds

if TYPE_CHECKING:
    from docker.models.containers import Container  # type: ignore
    from docker.models.networks import Network  # type: ignore


def _write_process_out(logs: bytes) -> None:
    with os.fdopen(sys.stdout.fileno(), "wb", closefd=False) as stdout:
        stdout.write(logs)
        stdout.flush()


def _get_free_port() -> str:
    with socket.socket() as sock:
        sock.bind(("", 0))
        return str(sock.getsockname()[1])


class ManagedClient(DockerClient):
    """DockerClient overload with container/network resource allocation context
    managers."""

    @contextmanager
    def _run_container(
        self, image: str, network_name: str, **kwargs
    ) -> Iterator["Container"]:
        cont = cast(
            "Container",
            self.containers.run(
                image, detach=True, remove=True, network=network_name, **kwargs
            ),
        )
        try:
            yield cont

        finally:
            cont.stop()

    @contextmanager
    def _docker_network(self, name: str = "tierkreis-net") -> Iterator[str]:
        network = cast("Network", self.networks.create(name, driver="bridge"))

        try:
            yield network.name or ""

        finally:
            network.remove()


class DockerRuntime(AbstractAsyncContextManager):
    """Context manager for setting up a containerised runtime + workers and
    return a connected client."""

    def __init__(
        self,
        image: str,
        worker_images: Optional[List[str]] = None,
        host_workers: Optional[List[Path]] = None,
        myqos_worker: Optional[str] = None,
        grpc_port: int = 8080,
        show_output: bool = False,
    ):
        self.grpc_port = grpc_port
        self.image = image
        self.worker_images = worker_images or []
        self.host_workers = host_workers or []
        self.show_output = show_output
        self.myqos_worker = myqos_worker
        self.ports = {"8080": str(self.grpc_port)}
        self._exit: Optional[Callable] = None

    async def __aenter__(self) -> RuntimeClient:
        client = ManagedClient.from_env()

        # ExitStack will hold the exits for all the contexts used
        # and if anything goes wrong in setup, everything done so far will be
        # exited in reverse order
        with ExitStack() as stack:
            command: List[str] = []
            for path in self.host_workers:
                port = stack.enter_context(self._start_host_worker(path))
                command.extend(
                    ["--worker-remote", f"http://host.docker.internal:{port}"]
                )

            network_name = stack.enter_context(client._docker_network())

            for i, image in enumerate(self.worker_images):
                container_name = (
                    stack.enter_context(
                        client._run_container(image, network_name, name=f"worker_{i}")
                    ).name
                    or ""
                )
                command.extend(["--worker-remote", f"http://{container_name}:80"])

            proc_env = {}

            if self.myqos_worker:
                # place mushroom authentication in environment if present
                log, pwd = _get_myqos_creds()
                if log:
                    proc_env["TIERKREIS_MYQOS_TOKEN"] = log
                if pwd:
                    proc_env["TIERKREIS_MYQOS_KEY"] = pwd

                command.extend(["--myqos-worker", self.myqos_worker])

            runtime_container = stack.enter_context(
                client._run_container(
                    self.image,
                    network_name,
                    command=command,
                    ports=self.ports,
                    environment=proc_env,
                )
            )

            succesful_start = False
            start_lines = []
            for line in runtime_container.logs(stream=True):
                start_lines.append(line)
                if "Server started" in str(line):
                    # server is ready to receive requests
                    succesful_start = True
                    break

            if not succesful_start:
                _write_process_out(b"\n".join(start_lines))
                # process has terminated unexpectedly
                raise RuntimeLaunchFailed()

            # nothing has gone wrong so far
            # so pop all the exits in the stack, and define the exit function to
            # be used later
            popped = stack.pop_all()

            def _exit():
                if self.show_output:
                    _write_process_out(runtime_container.logs())

                popped.close()

            self._exit = _exit

        async with Channel("127.0.0.1", self.grpc_port) as channel:
            return RuntimeClient(channel)

    async def __aexit__(
        self,
        __exc_type: Union[Type[BaseException], None],
        __exc_value: Union[BaseException, None],
        __traceback: Union[TracebackType, None],
    ) -> bool:
        if self._exit is not None:
            self._exit()
        return __exc_value is None

    @contextmanager
    def _start_host_worker(self, host_worker_path: Path) -> Iterator[str]:
        while True:
            free_port = _get_free_port()
            if free_port not in self.ports:
                break
        proc = subprocess.Popen(
            [f"{host_worker_path}/main.py", "--port", free_port],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        for line in cast(IO[bytes], proc.stdout):
            # wait for server to finish starting and announce port
            if free_port in str(line):
                break
        try:
            self.ports[free_port] = free_port
            yield free_port
        finally:
            proc.terminate()
