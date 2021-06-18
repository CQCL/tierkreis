from tierkreis.core import TierkreisGraph
from tierkreis.core.tierkreis_graph import TierkreisEdge
from tierkreis.core.types import IntType


def test_creation() -> None:
    tg = TierkreisGraph()
    n2 = tg.add_const(3)

    add = tg.add_function_node("python_nodes/add")

    tg.add_edge(n2.out_port.value, add.in_port.a)

    tg.register_input("in", add.in_port.b)
    tg.register_output("out", add.out_port.c)

    assert len(tg.nodes()) == 4
    assert len(tg.edges()) == 3

    assert tg.inputs == {"in": IntType()}
    assert tg.outputs == {"out": IntType()}

    assert tg.out_edges(add)[0] == TierkreisEdge(
        add.out_port.c, tg[tg.output_node_name].in_port.out, None
    )
