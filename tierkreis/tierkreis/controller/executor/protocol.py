from typing import Protocol
from uuid import UUID

from tierkreis.controller.data.location import Loc, WorkerCallArgs


class ControllerExecutor(Protocol):
    """The executor protocol defines how to run workers.

    An executor is responsible for running a worker(binary) in a given environment.

    """

    def command(
        self, launcher_name: str, workflow_id: UUID, loc: Loc, call_args: WorkerCallArgs
    ) -> str:
        """A command passed to subprocess that runs the worker."""
        ...
