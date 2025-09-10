from pathlib import Path
from uuid import UUID
from tierkreis.controller.data.location import Loc, WorkerCallArgs
from tierkreis.controller.executor.consts import BASH_TKR_DIR
from tierkreis.paths import Paths
from tierkreis.runner.commands import (
    DockerRun,
    HandleError,
    UvRun,
    WithCallArgs,
    TouchDone,
)


class DockerExecutor:
    """Executes workers in a docker container.

    Implements: :py:class:`tierkreis.controller.executor.protocol.ControllerExecutor`
    """

    def command(
        self, launcher_name: str, workflow_id: UUID, loc: Loc, call_args: WorkerCallArgs
    ) -> str:
        paths = Paths(workflow_id, Path(BASH_TKR_DIR))
        cmd = "main.py"
        cmd = WithCallArgs(paths.worker_call_args_path(loc))(cmd)
        cmd = UvRun(".")(cmd)
        cmd = TouchDone(paths.done_path(loc))(cmd)
        cmd = HandleError(
            paths.error_path(loc), paths.error_logs_path(loc), paths.logs_path()
        )(cmd)
        cmd = DockerRun(f"tkr_{launcher_name}")(cmd)
        return cmd
