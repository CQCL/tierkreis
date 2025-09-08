from pathlib import Path
from tierkreis.runner.commands import WithCallArgs


class ShellExecutor:
    """Executes workers in an unix shell.

    Implements: :py:class:`tierkreis.controller.executor.protocol.ControllerExecutor`
    """

    def __init__(self, registry_path: Path) -> None:
        self.launchers_path = registry_path

    def command(self, launcher_name: str, worker_call_args_path: Path) -> str:
        cmd = f"{self.launchers_path}/{launcher_name}"
        cmd = WithCallArgs(str(worker_call_args_path))(cmd)
        return cmd
