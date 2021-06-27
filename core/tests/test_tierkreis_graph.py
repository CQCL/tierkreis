from tierkreis.core import TierkreisGraph
from tierkreis.core.tierkreis_graph import NodePort, TierkreisEdge, TierkreisFunction
from tierkreis.core.types import IntType, TypeScheme, Row, GraphType


def test_creation() -> None:
    tg = TierkreisGraph()

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
    add = tg.add_node(add_func, a=3, b=tg.input.out.input)
    tg.set_outputs(output=add)

    id_g = TierkreisGraph()
    id_node = id_g.add_node("builtin/id", value=id_g.input.out.value)
    id_g.set_outputs(value=id_node.out.value)

    tg.add_box(id_g)

    deser_tg = TierkreisGraph.from_proto(tg.to_proto())

    for graph in (tg, deser_tg):

        assert len(graph.nodes()) == 5
        assert len(graph.edges()) == 3

        assert graph.inputs() == ["input"]
        assert graph.outputs() == ["output"]

        assert graph.out_edges(add)[0] == TierkreisEdge(
            add.out.value, NodePort(graph.output, "output"), None
        )
