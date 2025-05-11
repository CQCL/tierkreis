# /// script
# requires-python = ">=3.12"
# dependencies = ["tierkreis"]
#
# [tool.uv.sources]
# tierkreis = { path = "../../tierkreis", editable = true }
# ///
import json
from pathlib import Path
from uuid import UUID

from tierkreis import Labels
from tierkreis.controller import run_graph
from tierkreis.controller.data.graph import GraphData, Const, Func, Output, Input
from tierkreis.controller.data.location import Loc
from tierkreis.controller.storage.filestorage import ControllerFileStorage
from tierkreis.controller.executor.uv_executor import UvExecutor

root_loc = Loc()


def hello_graph() -> GraphData:
    """A graph that greets the subject."""
    g = GraphData()

    # We add a constant that yields the string "hello ".
    hello = g.add(Const("hello "))("value")

    # We add an input to the graph called "value".
    subject = g.add(Input("value"))("value")

    # We call the "concat" function from our worker.
    output = g.add(
        Func("hello_world_worker.greet", {"greeting": hello, "subject": subject})
    )("value")

    # We assign the output to the "value" label.
    g.add(Output({"value": output}))

    return g


def main() -> None:
    """Configure our workflow execution and run it to completion."""
    # Assign a fixed uuid for our workflow.
    workflow_id = UUID(int=100)
    storage = ControllerFileStorage(workflow_id, name="hello_world")
    # Clean the working directory if a prior workflow of that ID already exists
    storage.clean_graph_files()

    # Look for workers in the same directory as this file.
    registry_path = Path(__file__).parent
    executor = UvExecutor(registry_path=registry_path, logs_path=storage.logs_path)
    print("Starting workflow at location:", storage.logs_path)
    run_graph(
        storage,
        executor,
        hello_graph(),
        {Labels.VALUE: json.dumps("world!").encode()},
        polling_interval_seconds=0.1,
    )
    output = json.loads(storage.read_output(root_loc, Labels.VALUE))
    print(output)


if __name__ == "__main__":
    main()
