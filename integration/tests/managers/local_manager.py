"""Context manager for a local tierkreis server
when the binary is available on the system."""

import asyncio
import json
import os
import signal
import subprocess
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from threading import Thread
from typing import IO, Any, AsyncIterator, List, Optional, Union, cast

from grpclib.client import Channel
from tierkreis.client.server_client import RuntimeLaunchFailed


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
    workers: List[tuple[str, Path]],
    worker_uris: List[tuple[str, str]],
    port: int = 8080,
    show_output: bool = False,
    runtime_type_checking: Optional[str] = None,
    job_server: bool = False,
    checkpoint_endpoint: Optional[tuple[str, int]] = None,
) -> AsyncIterator[Channel]:
    """Provide a context for a local runtime running in a subprocess.

    :param executable: Path to server binary
    :type executable: Path
    :param workers: List of Locations with Path of worker server
    :type workers: List[str, Path]
    :param worker_uris: List of Locations with Uri of remote worker
    :type worker_uris: List[str, str]
    :param port: Localhost grpc port, defaults to "8080"
    :type port: str, optional
    :param show_output: Show server tracing/errors, defaults to False
    :type show_output: bool, optional
    :param runtime_type_checking: Type checking mode, defaults to None
    :type runtime_type_checking: str, optional
    :param job_server: Whether to start as a job server, defaults to False
    :type job_server: bool, optional
    :param checkpoint_endpoint: Tuple of (host, port) for checkpoint server,
        defaults to None
    :type checkpoint_endpoint: tuple[str, int], optional
    :yield: RuntimeClient
    :rtype: Iterator[RuntimeClient]
    """

    command: List[Union[str, Path]] = [executable, "-c"]

    config: dict[str, Any] = {"job_server": job_server}

    config["worker_path"] = [{"location": x, "path": str(y)} for x, y in workers]
    config["worker_uri"] = [{"location": x, "uri": str(y)} for x, y in worker_uris]

    if port:
        config["port"] = port

    if runtime_type_checking:
        config["runtime_type_checking"] = runtime_type_checking

    if checkpoint_endpoint:
        config["checkpoint_endpoint"] = checkpoint_endpoint
        assert job_server

    command.append(str(json.dumps(config)))
    proc = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE if show_output else subprocess.DEVNULL,
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
        async with Channel("localhost", port) as channel:
            yield channel

    finally:
        proc.send_signal(signal.SIGINT)

        await asyncio.sleep(1)  # FIXME deadlocks without this line (?)
        proc.kill()

        if show_output:
            # Ensure that output has been echoed (and wait for server to close stream)
            for t in echo_threads:
                t.join()
