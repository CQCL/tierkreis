"""Context manager for a local tierkreis server
 when the binary is available on the system."""
import asyncio
import os
import signal
import subprocess
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from threading import Thread
from typing import IO, AsyncIterator, List, Mapping, Optional, Union, cast

from grpclib.client import Channel

from .myqos_client import _get_myqos_creds
from .runtime_client import RuntimeLaunchFailed, ServerRuntime


def echo_thread(src: IO[bytes], dest: Union[int, str]):
    def run():
        # closefd=False only works when 'open'ing a 'fileno()'
        with open(dest, "wb", closefd=isinstance(dest, str)) as d:
            for line in src:
                d.write(line)
                d.flush()

    t = Thread(target=run)
    t.start()
    return t


def _wait_for_print(proc_out: IO[bytes], content: str):
    for line in proc_out:
        if content in str(line):
            break


@asynccontextmanager
async def local_runtime(
    executable: Path,
    workers: List[Path],
    grpc_port: int = 8080,
    show_output: bool = False,
    myqos_worker: Optional[str] = None,
    runtime_type_checking: Optional[str] = None,
    env_vars: Optional[Mapping[str, str]] = None,
) -> AsyncIterator[ServerRuntime]:
    """Provide a context for a local runtime running in a subprocess.

    :param executable: Path to server binary
    :type executable: Path
    :param workers: Paths of worker servers
    :type workers: List[Path]
    :param grpc_port: Localhost grpc port, defaults to "8080"
    :type grpc_port: str, optional
    :param show_output: Show server tracing/errors, defaults to False
    :type show_output: bool, optional
    :param myqos_worker: URL of Myqos-hosted runtime,
     to be used as worker, defaults to None
    :type myqos_worker: str, optional
    :yield: RuntimeClient
    :rtype: Iterator[RuntimeClient]
    """

    command: List[Union[str, Path]] = [executable]
    for worker in workers:
        command.extend(["--worker-path", worker])

    proc_env = os.environ.copy()
    if env_vars:
        proc_env.update(env_vars)

    if myqos_worker:
        # place mushroom authentication in environment if present
        log, pwd = _get_myqos_creds()
        if log:
            proc_env["TIERKREIS_MYQOS_TOKEN"] = log
        if pwd:
            proc_env["TIERKREIS_MYQOS_KEY"] = pwd

        command.extend(["--myqos-worker", myqos_worker])
    if grpc_port:
        proc_env["TIERKREIS_GRPC_PORT"] = str(grpc_port)

    if runtime_type_checking:
        command.extend(["--runtime-type-checking", runtime_type_checking])

    proc = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE if show_output else subprocess.DEVNULL,
        env=proc_env,
    )

    echo_threads = []
    if show_output:
        echo_threads.append(
            echo_thread(cast(IO[bytes], proc.stderr), sys.stderr.fileno())
        )

    proc_out = cast(IO[bytes], proc.stdout)
    _wait_for_print(proc_out, "Server started")
    # We opened stdout as a subprocess.PIPE, so we must read it
    # to prevent the buffer from filling up (which blocks the server)
    echo_threads.append(
        echo_thread(proc_out, sys.stdout.fileno() if show_output else os.devnull)
    )

    if proc.poll() is not None:
        # process has terminated unexpectedly
        for t in echo_threads:
            t.join()
        raise RuntimeLaunchFailed()

    try:
        async with Channel("localhost", grpc_port) as channel:
            yield ServerRuntime(channel)

    finally:
        proc.send_signal(signal.SIGINT)

        await asyncio.sleep(1)  # FIXME deadlocks without this line (?)
        proc.kill()

        if show_output:
            # Ensure that output has been echoed (and wait for server to close stream)
            for t in echo_threads:
                t.join()
