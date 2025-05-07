import subprocess
from pathlib import Path

from tierkreis.exceptions import TierkreisError


class ShellExecutor:
    def __init__(self, registry_path: Path, logs_path: Path) -> None:
        self.launchers_path = registry_path
        self.logs_path = logs_path
        self.errors_path = logs_path

    def run(self, launcher_name: str, node_definition_path: Path) -> None:
        launcher_path = self.launchers_path / launcher_name
        self.errors_path = node_definition_path.parent / "errors"
        if not launcher_path.exists():
            raise TierkreisError(f"Launcher not found: {launcher_name}.")

        if not launcher_path.is_file():
            raise TierkreisError(f"Expected launcher file. Found: {launcher_path}.")

        with open(self.logs_path, "a") as lfh:
            with open(self.errors_path, "a") as efh:
                subprocess.Popen(
                    [f"{self.launchers_path}/{launcher_name}", node_definition_path],
                    start_new_session=True,
                    stderr=efh,
                    stdout=lfh,
                )
