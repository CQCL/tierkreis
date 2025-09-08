import logging
from pathlib import Path

from tierkreis.runner.commands import UvRun, WithCallArgs

logger = logging.getLogger(__name__)


class UvExecutor:
    """Executes workers in an UV python environment.

    Implements: :py:class:`tierkreis.controller.executor.protocol.ControllerExecutor`
    """

    def __init__(self, registry_path: Path) -> None:
        self.launchers_path = registry_path

    def command(self, launcher_name: str, worker_call_args_path: Path) -> str:
        cmd = f"{self.launchers_path}/{launcher_name}/main.py"
        cmd = WithCallArgs(str(worker_call_args_path))(cmd)
        cmd = UvRun(f"{self.launchers_path}/{launcher_name}")(cmd)
        return cmd
