# /// script
# requires-python = ">=3.12"
# dependencies = ["tierkreis"]
#
# [tool.uv.sources]
# tierkreis = { path = "../../python" }
# ///
import json
from pathlib import Path
from uuid import uuid4

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

    # We add a contant that yields the string "hello ".
    hello = g.add(Const("hello "))("value")

    # We add an input to the graph called "value".
    subject = g.add(Input("value"))("value")

    # We call the "greet" function from our worker.
    output = g.add(
        Func("hello_world_worker.greet", {"greeting": hello, "subject": subject})
    )("value")

    # We assign the output to the "value" label.
    g.add(Output({"value": output}))

    return g


def main() -> None:
    """Configure our workflow execution and run it to completion."""
    storage = ControllerFileStorage(uuid4())
    executor = UvExecutor(
        registry_path=Path(__file__).parent, logs_path=storage.logs_path
    )
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
