from typing import Protocol
from uuid import UUID

from tierkreis.controller.data.location import Loc


class ControllerExecutor(Protocol):
    """The executor protocol defines how to run workers.

    An executor is responsible for running a worker(binary) in a given environment.

    """

    def command(self, launcher_name: str, workflow_id: UUID, loc: Loc) -> str:
        """A command passed to subprocess that runs the worker."""
        ...
