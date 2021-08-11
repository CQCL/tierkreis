import pytest
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
    add = tg.add_node(add_func, a=3, b=tg.input["input"])
    tg.set_outputs(output=add)

    id_g = TierkreisGraph()
    id_node = id_g.add_node("builtin/id", value=id_g.input["value"])
    id_g.set_outputs(value=id_node["value"])

    tg.add_box(id_g)

    deser_tg = TierkreisGraph.from_proto(tg.to_proto())

    for graph in (tg, deser_tg):

        assert len(graph.nodes()) == 5
        assert len(graph.edges()) == 3

        assert graph.inputs() == ["input"]
        assert graph.outputs() == ["output"]

        assert graph.out_edges(add)[0] == TierkreisEdge(
            add["value"], NodePort(graph.output, "output"), None
        )


def test_insert_subgraph() -> None:
    subgraph = TierkreisGraph()

    pair_port = subgraph.make_pair(subgraph.input["one"], subgraph.input["two"])
    first_p, second_p = subgraph.unpack_pair(pair_port)
    subgraph.delete(second_p)
    subgraph.set_outputs(sub_out=first_p)

    main_g = TierkreisGraph()
    subgraph_outs = main_g.insert_graph(
        subgraph, "subgraph::", one=main_g.input["in1"], two=3
    )
    assert (
        sum(node_name.startswith("subgraph::") for node_name in main_g.nodes())
        == len(subgraph.nodes()) - 2
    )
    assert list(subgraph_outs.keys()) == ["sub_out"]
    make_p = main_g.make_pair(main_g.input["in2"], subgraph_outs["sub_out"])

    main_g.set_outputs(value=make_p)

    assert len(main_g.nodes()) == 7
    assert len(main_g.edges()) == 7

    with pytest.raises(TierkreisGraph.DuplicateNodeName) as e:  # type: ignore ; pytest doesn't like custom exception
        _ = main_g.insert_graph(
            subgraph, "subgraph::", one=main_g.input["newin1"], two=4
        )

    assert e.value.name == "subgraph::NewNode(0)"
