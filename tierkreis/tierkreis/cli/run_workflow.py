from pathlib import Path
from uuid import UUID, uuid4
import json
import logging

from tierkreis import Labels
from tierkreis.controller import run_graph
from tierkreis.controller.data.graph import GraphData
from tierkreis.controller.data.location import Loc
from tierkreis.controller.storage.filestorage import ControllerFileStorage
from tierkreis.controller.executor.uv_executor import UvExecutor

logger = logging.getLogger(__name__)


def run_workflow(
    graph: GraphData,
    inputs: dict[str, bytes],
    name: str | None = None,
    run_id: int | None = None,
    log_level: int | str = logging.INFO,
    registry_path: Path | None = None,
    print_output: bool = False,
    **kwargs,
) -> None:
    """Run a workflow."""
    logging.basicConfig(
        format="%(asctime)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
        level=log_level,
    )

    if run_id is None:
        workflow_id = uuid4()
    else:
        workflow_id = UUID(int=run_id)
    storage = ControllerFileStorage(workflow_id, name=name)
    if registry_path is None:
        registry_path = Path(__file__).parent
    executor = UvExecutor(registry_path=registry_path, logs_path=storage.logs_path)
    logging.info("Starting workflow at location: %s", storage.logs_path)

    run_graph(
        storage,
        executor,
        graph,
        inputs,
        **{
            k: v
            for k, v in kwargs.items()
            if k in ["n_iterations", "polling_interval_seconds"]
        },
    )
    if print_output:
        output = json.loads(storage.read_output(Loc(), Labels.VALUE))
        print(output)
