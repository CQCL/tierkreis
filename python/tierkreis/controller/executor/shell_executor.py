import os
from pathlib import Path

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

        stderr = self.launchers_path / "_stderr"
        cmd = f"{self.launchers_path}/{launcher_name} {node_definition_path} >>{stderr} 2>&1"
        os.system(cmd)
