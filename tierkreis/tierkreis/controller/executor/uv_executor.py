import logging
from pathlib import Path
from uuid import UUID

from tierkreis.controller.data.location import Loc, WorkerCallArgs
from tierkreis.controller.executor.consts import BASH_TKR_DIR
from tierkreis.paths import Paths
from tierkreis.runner.commands import HandleError, TouchDone, UvRun, WithCallArgs

logger = logging.getLogger(__name__)


class UvExecutor:
    """Executes workers in an UV python environment.

    Implements: :py:class:`tierkreis.controller.executor.protocol.ControllerExecutor`
    """

    def __init__(self, registry_path: Path) -> None:
        self.launchers_path = registry_path

    def command(
        self, launcher_name: str, workflow_id: UUID, loc: Loc, call_args: WorkerCallArgs
    ) -> str:
        paths = Paths(workflow_id, Path(BASH_TKR_DIR))
        cmd = f"{self.launchers_path}/{launcher_name}/main.py"
        cmd = WithCallArgs(paths.worker_call_args_path(loc))(cmd)
        cmd = UvRun(f"{self.launchers_path}/{launcher_name}")(cmd)
        cmd = HandleError(
            paths.error_path(loc), paths.error_logs_path(loc), paths.logs_path()
        )(cmd)
        cmd = TouchDone(paths.done_path(loc))(cmd)
        return cmd
