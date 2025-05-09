# /// script
# requires-python = ">=3.12"
# dependencies = ["tierkreis"]
#
# [tool.uv.sources]
# tierkreis = { path = "../../tierkreis", editable = true }
# ///
import json
from pathlib import Path

from tierkreis import Labels
from tierkreis.controller.data.graph import GraphData, Const, Func, Output, Input
from tierkreis.controller.data.location import Loc
from tierkreis.cli.run_workflow import run_workflow

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
    run_workflow(
        hello_graph(),
        {Labels.VALUE: json.dumps("world!").encode()},
        name="hello_world",
        run_id=100,  # Assign a fixed uuid for our workflow.
        registry_path=Path(
            __file__
        ).parent,  # Look for workers in the same directory as this file.
        polling_interval_seconds=0.1,
        print_output=True,
    )


if __name__ == "__main__":
    main()
