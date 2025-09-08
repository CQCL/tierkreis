import json
import subprocess
from pathlib import Path

from tierkreis.controller.data.location import WorkerCallArgs
from tierkreis.controller.executor.run_command import run_command
from tierkreis.exceptions import TierkreisError
from tierkreis.runner.commands import WithCallArgs


class ShellExecutor:
    """Executes workers in an unix shell.

    Implements: :py:class:`tierkreis.controller.executor.protocol.ControllerExecutor`
    """

    def __init__(self, registry_path: Path, workflow_dir: Path) -> None:
        self.launchers_path = registry_path
        self.logs_path = workflow_dir / "logs"
        self.errors_path = workflow_dir / "logs"
        self.workflow_dir = workflow_dir

    def run(self, launcher_name: str, worker_call_args_path: Path) -> None:
        launcher_path = self.launchers_path / launcher_name
        self.errors_path = worker_call_args_path.parent / "errors"

        if not launcher_path.exists():
            raise TierkreisError(f"Launcher not found: {launcher_name}.")

        if launcher_path.is_dir() and not (launcher_path / "main.sh").exists():
            raise TierkreisError(f"Expected launcher file. Got {launcher_path}.")

        with open(worker_call_args_path) as fh:
            call_args = WorkerCallArgs(**json.load(fh))

        cmd = WithCallArgs(str(worker_call_args_path))
        run_command(cmd(f"{self.launchers_path}/{launcher_name}"), call_args)
