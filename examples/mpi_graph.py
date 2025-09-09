# /// script
# requires-python = ">=3.12"
# dependencies = ["tierkreis"]
#
# [tool.uv.sources]
# tierkreis = { path = "../tierkreis", editable = true }
# ///
import json
from pathlib import Path
import subprocess
from uuid import UUID
from tierkreis.builder import GraphBuilder
from tierkreis.controller import run_graph
from tierkreis.controller.data.models import TKR
from tierkreis.controller.storage.filestorage import ControllerFileStorage

from tierkreis.exceptions import TierkreisError
from tierkreis.storage import read_outputs

from example_workers.mpi_worker.stubs import double


class CustomExecutor:
    def __init__(
        self, registry_path: Path, workflow_dir: Path, n_processes: int = 4
    ) -> None:
        self.launchers_path = registry_path
        self.logs_path = workflow_dir / "logs"
        self.errors_path = workflow_dir / "logs"
        self.workflow_dir = workflow_dir
        self.command = [
            "mpirun",
            "-n",
            f"{n_processes}",
        ]

    def run(self, launcher_name: str, worker_call_args_path: Path) -> None:
        launcher_path = self.launchers_path / launcher_name
        self.errors_path = (
            self.workflow_dir.parent / worker_call_args_path.parent / "errors"
        )
        if not launcher_path.exists():
            raise TierkreisError(f"Launcher not found: {launcher_name}.")

        if not launcher_path.is_file():
            raise TierkreisError(f"Expected launcher file. Found: {launcher_path}.")
        self.command += [
            str(launcher_path),
            str(self.workflow_dir.parent / worker_call_args_path),
        ]
        with open(self.logs_path, "a") as lfh:
            with open(self.errors_path, "a") as efh:
                subprocess.Popen(
                    self.command,
                    start_new_session=True,
                    stderr=efh,
                    stdout=lfh,
                )


def mpi_doubler() -> GraphBuilder:
    graph = GraphBuilder(inputs_type=TKR[list[int]], outputs_type=double.out())
    doubled = graph.task(double(graph.inputs))
    graph.outputs(doubled)
    return graph


def run() -> None:
    workflow_id = UUID(int=25)
    storage = ControllerFileStorage(workflow_id, name="mpi_builder", do_cleanup=True)
    graph = mpi_doubler()
    registry_path = Path(__file__).parent / "example_workers/mpi_worker/build"
    executor = CustomExecutor(
        registry_path=registry_path, workflow_dir=storage.workflow_dir
    )
    inputs = json.dumps([10, 20, 30, 40])
    run_graph(storage, executor, graph.data, inputs)
    output = read_outputs(graph, storage)
    print(output)


if __name__ == "__main__":
    run()
