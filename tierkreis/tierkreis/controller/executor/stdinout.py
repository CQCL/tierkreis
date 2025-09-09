import json
import subprocess
from pathlib import Path

from tierkreis.controller.data.location import WorkerCallArgs
from tierkreis.exceptions import TierkreisError


class StdInOut:
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

        if launcher_path.is_dir() and not (launcher_path / "main.sh").is_file():
            raise TierkreisError(f"Expected launcher file. Got {launcher_path}/main.sh")

        if launcher_path.is_dir() and (launcher_path / "main.sh").is_file():
            launcher_path = launcher_path / "main.sh"

        with open(self.workflow_dir.parent / worker_call_args_path) as fh:
            call_args = WorkerCallArgs(**json.load(fh))

        input_file = self.workflow_dir.parent / list(call_args.inputs.values())[0]
        output_file = self.workflow_dir.parent / list(call_args.outputs.values())[0]
        done_path = self.workflow_dir.parent / call_args.done_path

        with open(self.workflow_dir.parent / self.logs_path, "a") as lfh:
            with open(self.workflow_dir.parent / self.errors_path, "a") as efh:
                proc = subprocess.Popen(
                    ["bash"],
                    start_new_session=True,
                    stdin=subprocess.PIPE,
                    stderr=efh,
                    stdout=lfh,
                )
                proc.communicate(
                    f"{launcher_path} <{input_file} >{output_file} && touch {done_path}".encode(),
                    timeout=3,
                )
