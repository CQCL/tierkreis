from pathlib import Path
import subprocess
import multiprocessing


def run_subprocess(args, stderr: Path):
    subprocess.Popen(args=args)


class ShellExecutor:
    def __init__(self, registry_path: Path) -> None:
        self.launchers_path = registry_path

    def run(self, launcher_name: str, node_definition_path: Path) -> None:
        args = [f"{self.launchers_path}/{launcher_name}", node_definition_path]
        stderr = node_definition_path.parent / "_stderr"
        stderr.touch()
        multiprocessing.Process(target=run_subprocess, args=[args, stderr]).start()
