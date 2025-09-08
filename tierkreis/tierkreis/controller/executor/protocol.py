from pathlib import Path
from typing import Protocol


class ControllerExecutor(Protocol):
    """The executor protocol defines how to run workers.

    An executor is responsible for running a worker(binary) in a given environment.

    """

    def command(self, launcher_name: str, worker_call_args_path: Path) -> str:
        """A command passed to subprocess that runs the worker."""
        ...
