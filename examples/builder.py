from pathlib import Path
from tierkreis.cli.run_workflow import run_workflow

from tierkreis.controller.data.graph import GraphData
from tierkreis import Labels


def loop_body() -> GraphData:
    g = GraphData()
    g.input().const(1).const(10).func("builtins.iadd", {"a": 0, "b": 1}).func(
        "builtins.igt", {"a": 2, "b": 3}
    ).output({Labels.VALUE: -2, "should_continue": -1})
    return g


f = GraphData()
f.const(6).loop(loop_body(), "should_continue", {Labels.VALUE: -1}).output()


inputs = {}
run_workflow(
    f,
    inputs,
    name="exp",
    run_id=55,  # Assign a fixed uuid for our workflow.
    registry_path=Path(__file__).parent / "example_workers",
    # Look for workers in the same directory.
    use_uv_worker=True,
    print_output=True,
)
