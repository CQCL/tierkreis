from pathlib import Path
import sys
from uuid import UUID
from tierkreis.consts import PACKAGE_PATH
from tierkreis.controller.data.location import Loc, WorkerCallArgs
from tierkreis.controller.executor.consts import BASH_TKR_DIR
from tierkreis.paths import Paths
from tierkreis.runner.commands import HandleError, WithCallArgs, TouchDone


class BuiltinsExecutor:
    """Executes a builtin task using the current interpreter.

    Implements: :py:class:`tierkreis.controller.executor.protocol.ControllerExecutor`
    """

    def command(
        self, launcher_name: str, workflow_id: UUID, loc: Loc, call_args: WorkerCallArgs
    ) -> str:
        paths = Paths(workflow_id, Path(BASH_TKR_DIR))
        cmd = f"{sys.executable} {PACKAGE_PATH}/tierkreis/builtins/main.py"
        cmd = WithCallArgs(paths.worker_call_args_path(loc))(cmd)
        cmd = HandleError(
            paths.error_path(loc), paths.error_logs_path(loc), paths.logs_path()
        )(cmd)
        cmd = TouchDone(paths.done_path(loc))(cmd)
        return cmd
