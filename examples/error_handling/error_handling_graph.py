# /// script
# requires-python = ">=3.12"
# dependencies = ["tierkreis"]
#
# [tool.uv.sources]
# tierkreis = { path = "../../tierkreis" }
# ///
import json
from pathlib import Path
from uuid import UUID

from tierkreis import Labels
from tierkreis.controller import run_graph
from tierkreis.controller.data.graph import GraphData, Func, Output
from tierkreis.controller.data.location import Loc
from tierkreis.controller.storage.filestorage import ControllerFileStorage
from tierkreis.controller.executor.uv_executor import UvExecutor

root_loc = Loc()


def error_graph() -> GraphData:
    """A graph that errors."""
    g = GraphData()

    output = g.add(Func("error_worker.fail", {}))("value")

    g.add(Output({"value": output}))

    return g


def main() -> None:
    """Configure our workflow execution and run it to completion."""
    # Assign a fixed uuid for our workflow.
    workflow_id = UUID(int=103)
    storage = ControllerFileStorage(workflow_id, name="error_handling")

    # Look for workers in the same directory as this file.
    registry_path = Path(__file__).parent
    executor = UvExecutor(registry_path=registry_path, logs_path=storage.logs_path)
    print("Starting workflow at location:", storage.logs_path)
    run_graph(
        storage,
        executor,
        error_graph(),
        {Labels.VALUE: json.dumps("world!").encode()},
        polling_interval_seconds=0.1,
    )
    output = storage.read_errors(root_loc)
    print(output)


if __name__ == "__main__":
    main()
