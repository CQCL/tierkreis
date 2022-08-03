"""Docker container management for tierkreis runtime servers and workers."""

import asyncio
import os
import socket
import subprocess
import sys
from contextlib import AsyncExitStack, asynccontextmanager, contextmanager
from pathlib import Path
from typing import (
    IO,
    TYPE_CHECKING,
    AsyncIterator,
    Iterator,
    List,
    Optional,
    Tuple,
    ValuesView,
    cast,
)

from docker import DockerClient  # type: ignore
from grpclib.client import Channel

from .myqos_client import _get_myqos_creds
from .runtime_client import RuntimeClient, RuntimeLaunchFailed

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


@asynccontextmanager
async def docker_runtime(
    image: str,
    worker_images: Optional[List[Tuple[str, str]]] = None,
    host_workers: Optional[List[Path]] = None,
    myqos_worker: Optional[str] = None,
    grpc_port: int = 8090,
    show_output: bool = False,
) -> AsyncIterator[RuntimeClient]:
    """Context manager for setting up a containerised runtime + workers and
    return a connected client.

    :param image: name of tierkreis server image
    :type image: str
    :param worker_images: list of pairs of worker images and paths to worker
        executables inside them, e.g. [("cqc/tierkreis-workers",
        "/root/workers/pytket_worker"), ("cqc/tierkreis-workers",
        "/root/workers/qermit_worker")], defaults to None
    :type worker_images: Optional[List[Tuple[str, str]]], optional
    :param host_workers: List of paths to local workers, e.g.
        ["../workers/pytket_worker"], defaults to None
    :type host_workers: Optional[List[Path]], optional
    :param myqos_worker: "Host address of myqos worker", defaults toNone
    :type myqos_worker: Optional[str], optional
    :param grpc_port: Port for server, defaults to 8090
    :type grpc_port: int, optional
    :param show_output: Whether to print server logs on exit, defaults to False
    :type show_output: bool, optional
    :yield: RuntimeClient
    :rtype: Iterator[AsyncIterator[RuntimeClient]]
    """

    worker_images = worker_images or []
    host_workers = host_workers or []
    container_to_host_ports = {"8080": str(grpc_port)}

    client = ManagedClient.from_env()

    # ExitStack will hold the exits for all the contexts used
    # and if anything goes wrong in setup, everything done so far will be
    # exited in reverse order
    async with AsyncExitStack() as stack:
        command: List[str] = []
        for path in host_workers:
            port = await stack.enter_async_context(
                _start_host_worker(container_to_host_ports.values(), path)
            )
            command.extend(["--worker-remote", f"http://host.docker.internal:{port}"])

        network_name = stack.enter_context(client._docker_network())

        worker_coros = []
        for i, (worker_image, container_path) in enumerate(worker_images):
            # worker needs given name for connection to work
            container_name = f"worker_{i}"
            work_cont = stack.enter_context(
                client._run_container(
                    worker_image,
                    network_name,
                    name=container_name,
                    command=[
                        container_path + "/main.py",
                        "--port",
                        "80",
                    ],
                )
            )

            worker_coros.append(
                _check_start(work_cont, "Started worker server on port")
            )
            command.extend(["--worker-remote", f"http://{container_name}:80"])

        await asyncio.gather(*worker_coros)
        proc_env = {}

        if myqos_worker:
            # place mushroom authentication in environment if present
            log, pwd = _get_myqos_creds()
            if log:
                proc_env["TIERKREIS_MYQOS_TOKEN"] = log
            if pwd:
                proc_env["TIERKREIS_MYQOS_KEY"] = pwd

            command.extend(["--myqos-worker", myqos_worker])

        runtime_container = stack.enter_context(
            client._run_container(
                image,
                network_name,
                command=command,
                ports=container_to_host_ports,
                environment=proc_env,
            )
        )

        await _check_start(runtime_container, "Server started")

        async with Channel("localhost", grpc_port) as channel:
            yield RuntimeClient(channel)

        if show_output:
            _write_process_out(runtime_container.logs())


async def _check_start(container: "Container", check_str: str):
    start_lines = []
    for line in container.logs(stream=True):
        start_lines.append(line)
        if check_str in str(line):
            # server is ready to receive requests
            return
        await asyncio.sleep(1)

    # failed to start correctly
    _write_process_out(b"\n".join(start_lines))
    raise RuntimeLaunchFailed()


@asynccontextmanager
async def _start_host_worker(
    ports_to_avoid: ValuesView[str], host_worker_path: Path
) -> AsyncIterator[str]:
    while True:
        free_port = _get_free_port()
        if free_port not in ports_to_avoid:
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
        await asyncio.sleep(1)
    try:
        yield free_port
    finally:
        proc.terminate()
