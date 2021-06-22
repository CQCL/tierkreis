from tierkreis.core import TierkreisGraph
from tierkreis.core.tierkreis_graph import TierkreisEdge, TierkreisFunction
from tierkreis.core.types import IntType, TypeScheme, Row, GraphType


def test_creation() -> None:
    tg = TierkreisGraph()
    n2 = tg.add_const(3)

    add_func = TierkreisFunction(
        name="python_nodes/add",
        type_scheme=TypeScheme(
            variables={},
            constraints=[],
            body=GraphType(
                inputs=Row(content={"b": IntType(), "a": IntType()}, rest=None),
                outputs=Row(content={"value": IntType()}, rest=None),
            ),
        ),
        docs="",
    )
    add = tg.add_function_node(add_func)
    tg.add_edge(n2.out_port.value, add.in_port.a)

    tg.register_input("in", add.in_port.b)
    tg.register_output("out", add.out_port.value)

    assert len(tg.nodes()) == 4
    assert len(tg.edges()) == 3

    assert tg.inputs == {"in": IntType()}
    assert tg.outputs == {"out": IntType()}

    assert tg.out_edges(add)[0] == TierkreisEdge(
        add.out_port.value, tg[tg.output_node_name].in_port.out, None
    )
