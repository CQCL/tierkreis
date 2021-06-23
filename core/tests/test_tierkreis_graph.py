from tierkreis.core import TierkreisGraph
from tierkreis.core.tierkreis_graph import NodePort, TierkreisEdge, TierkreisFunction
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
    add = tg.add_node(add_func, a=n2.out.value, b=tg.input.out.input)
    tg.set_outputs(output=add.out.value)

    assert len(tg.nodes()) == 4
    assert len(tg.edges()) == 3

    assert tg.inputs() == ["input"]
    assert tg.outputs() == ["output"]

    assert tg.out_edges(add)[0] == TierkreisEdge(
        add.out.value, NodePort(tg.output, "output"), None
    )
