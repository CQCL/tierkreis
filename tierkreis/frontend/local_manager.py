"""Context manager for a local tierkreis server
 when the binary is available on the system."""
import os
import signal
import subprocess
import asyncio
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import IO, List, Optional, Union, cast, AsyncIterator

from grpclib.client import Channel

from .runtime_client import RuntimeClient, RuntimeLaunchFailed
from .myqos_client import _get_myqos_creds


def _wait_for_print(proc: subprocess.Popen, content: str):
    for line in cast(IO[bytes], proc.stdout):
        if content in str(line):
            break


@asynccontextmanager
async def local_runtime(
    executable: Path,
    workers: Optional[List[Path]] = None,
    grpc_port: int = 8080,
    show_output: bool = False,
    myqos_worker: Optional[str] = None,
) -> AsyncIterator[RuntimeClient]:
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
    parent_dir = Path(__file__).parent

    workers = workers or [
        parent_dir / "../../tests/worker_test",
    ]

    command: List[Union[str, Path]] = [executable]
    for worker in workers:
        command.extend(["--worker-path", worker])

    proc_env = os.environ.copy()

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

    proc = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE if show_output else subprocess.DEVNULL,
        env=proc_env,
    )

    _wait_for_print(proc, "Server started")

    def write_process_out(process: subprocess.Popen) -> None:
        # get remaining output
        out, errs = proc.communicate()
        if errs:
            with os.fdopen(sys.stderr.fileno(), "wb", closefd=False) as stderr:
                stderr.write(errs)
        with os.fdopen(sys.stdout.fileno(), "wb", closefd=False) as stdout:
            if out:
                stdout.write(out)
            stdout.flush()

    if proc.poll() is not None:
        # process has terminated unexpectedly
        write_process_out(proc)
        raise RuntimeLaunchFailed()

    try:
        async with Channel("localhost", grpc_port) as channel:
            yield RuntimeClient(channel)

    finally:
        proc.send_signal(signal.SIGINT)
        _wait_for_print(proc, "shutdown complete")

        await asyncio.sleep(1)  # FIXME deadlocks without this line
        proc.kill()
        if show_output:
            write_process_out(proc)
