from pathlib import Path
from tierkreis.cli.run_workflow import run_workflow

from tierkreis.controller.data.graph import GraphData
from tierkreis.controller.data.graph_builder import AutoGraphBuilder, GraphBuilder
from tierkreis import Labels


def loop_body() -> GraphData:
    g = AutoGraphBuilder()
    g.input()
    g.const(1)
    g.const(10)
    g.func("builtins.iadd", {"a": 0, "b": 1})
    g.func("builtins.igt", {"a": 2, "b": 3})
    g.output({Labels.VALUE: -2, "should_continue": -1})
    return g.instantiate_graph()


f = GraphBuilder()
f.output(f.loop(loop_body(), "should_continue", f.const(6)))


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
