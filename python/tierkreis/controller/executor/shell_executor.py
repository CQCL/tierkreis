import subprocess
from pathlib import Path
from typing import Optional

from tierkreis.exceptions import TierkreisError


class ShellExecutor:
    def __init__(self, registry_path: Path) -> None:
        self.launchers_path = registry_path

    def run(self, launcher_name: str, node_definition_path: Path) -> None:
        launcher_path = self.launchers_path / launcher_name
        if not launcher_path.exists():
            raise TierkreisError(f"Launcher not found: {launcher_name}.")

        if not launcher_path.is_file():
            raise TierkreisError(f"Expected launcher file. Found: {launcher_path}.")

        args = [f"{self.launchers_path}/{launcher_name}", node_definition_path]
        subprocess.Popen(args, start_new_session=True)
