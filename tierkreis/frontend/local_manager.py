"""Context manager for a local tierkreis server
 when the binary is available on the system."""
import os
import signal
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import IO, Iterator, List, Optional, Union, cast

from .runtime_client import RuntimeClient, RuntimeLaunchFailed


@contextmanager
def local_runtime(
    executable: Path,
    workers: Optional[List[Path]] = None,
    http_port: str = "8080",
    show_output: bool = False,
) -> Iterator[RuntimeClient]:
    """Provide a context for a local runtime running in a subprocess.

    :param executable: Path to server binary
    :type executable: Path
    :param workers: Paths of worker servers
    :type workers: List[Path]
    :param http_port: Localhost http port, defaults to "8080"
    :type http_port: str, optional
    :param grpc_port: Localhost grpc port, defaults to "9090"
    :type grpc_port: str, optional
    :param show_output: Show server tracing/errors, defaults to False
    :type show_output: bool, optional
    :yield: RuntimeClient
    :rtype: Iterator[RuntimeClient]
    """
    parent_dir = Path(__file__).parent

    default_workers = [
        parent_dir / "../../../workers/worker_test",
        parent_dir / "../../../workers/pytket_worker",
    ]

    command: List[Union[str, Path]] = [executable]
    for worker in list(map(str, default_workers)):
        command.extend(["--worker-path", worker])
    if workers:
        for worker in list(map(str, workers)):
            command.extend(["--worker-path", worker])

    proc_env = os.environ.copy()
    proc_env["TIERKREIS_HTTP_PORT"] = http_port
    with subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        env=proc_env,
    ) as proc:

        lines = []
        for line in cast(IO[bytes], proc.stdout):
            lines.append(line)
            if "Server started" in str(line):
                # server is ready to receive requests
                break

        def write_process_out(process: subprocess.Popen) -> None:
            # get remaining output
            out, errs = process.communicate()

            if errs:
                with os.fdopen(sys.stderr.fileno(), "wb", closefd=False) as stderr:
                    stderr.write(errs)
            with os.fdopen(sys.stdout.fileno(), "wb", closefd=False) as stdout:
                for line in lines:
                    stdout.write(line)

                if out:
                    stdout.write(out)
                stdout.flush()

        if proc.poll() is not None:
            # process has terminated unexpectedly
            write_process_out(proc)
            raise RuntimeLaunchFailed()

        try:
            yield RuntimeClient(f"http://127.0.0.1:{http_port}")
        finally:
            if show_output:
                proc.send_signal(signal.SIGINT)
                write_process_out(proc)
