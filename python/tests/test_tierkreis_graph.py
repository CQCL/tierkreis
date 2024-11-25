from dataclasses import dataclass
from typing import Any, Iterable, Optional

import pytest

from tierkreis.core import TierkreisGraph
from tierkreis.core.function import FunctionName
from tierkreis.core.tierkreis_graph import (
    BoxNode,
    FunctionNode,
    NodePort,
    NodeRef,
    TierkreisEdge,
)
from tierkreis.core.types import (
    IntType,
    StructType,
    TierkreisType,
    UnionTag,
    VariantType,
    VarType,
)
from tierkreis.core.values import (
    FloatValue,
    IntValue,
    MapValue,
    TierkreisValue,
    TierkreisVariant,
    VecValue,
)


def count(i: Iterable[Any]) -> int:
    return sum(1 for _ in i)


def test_creation_roundtrip() -> None:
    tg = TierkreisGraph()

    add = tg.add_func("iadd", a=tg.add_const(3), b=tg.input["input"])
    tg.set_outputs(output=add)

    id_g = TierkreisGraph()
    id_node = id_g.add_func("id", 2, value=id_g.input["value"])
    id_g.set_outputs(value=id_node["value"])

    b = tg.add_box(id_g)

    deser_tg = TierkreisGraph.from_proto(tg.to_proto())

    for graph in (tg, deser_tg):
        assert count(graph.nodes()) == 5
        assert count(graph.edges()) == 3

        assert graph.inputs() == ["input"]
        assert graph.outputs() == ["output"]

        add_node = NodeRef(add.idx, graph)
        assert graph[add_node] == FunctionNode(FunctionName.parse("iadd"))
        assert graph[add_node] != FunctionNode(FunctionName.parse("iadd"), 0)
        assert next(graph.out_edges(add)) == TierkreisEdge(
            add_node["value"], NodePort(graph.output, "output"), None
        )

        boxn = graph[b.idx]
        assert isinstance(boxn, BoxNode)
        assert boxn.graph[id_node.idx] == FunctionNode(FunctionName.parse("id"), 2)


def test_insert_subgraph() -> None:
    subgraph = TierkreisGraph()

    pair_port = subgraph.make_pair(subgraph.input["one"], subgraph.input["two"])
    first_p, second_p = subgraph.unpack_pair(pair_port)
    subgraph.discard(second_p)
    subgraph.set_outputs(sub_out=first_p)

    main_g = TierkreisGraph()
    two = main_g.add_const(3)
    main_nodes_before = main_g.n_nodes
    sub_nodes_before = subgraph.n_nodes
    subgraph_outs = main_g.insert_graph(subgraph, one=main_g.input["in1"], two=two)
    assert main_g.n_nodes == (sub_nodes_before + main_nodes_before) - 2

    assert list(subgraph_outs.keys()) == ["sub_out"]
    make_p = main_g.make_pair(main_g.input["in2"], subgraph_outs["sub_out"])

    main_g.set_outputs(value=make_p)

    assert count(main_g.nodes()) == 7
    assert count(main_g.edges()) == 7


def test_value_topython():
    convertible_vals = (
        1,
        "two",
        False,
        2.3,
        [1, 2],
        ("a", 4),
        {"asf": 3, "fsd": 4},
        TierkreisVariant("mylabel", 5),
        None,
    )

    for val in convertible_vals:
        assert TierkreisValue.from_python(val).try_autopython() == val

    fail_vals = ([1, 2.2], {"asd": 3, "fgh": False})
    for val in fail_vals:
        assert TierkreisValue.from_python(val).try_autopython() is None


@dataclass
class Foo:
    head: int
    tail: Optional["Foo"]


def test_type_from_python():
    t = TierkreisType.from_python(Foo)
    assert isinstance(t, StructType)
    fields = t.shape.content
    tail = fields.pop("tail")
    assert isinstance(tail, VariantType)
    some = tail.shape.content["__py_union_foo"]
    assert isinstance(some, VarType) and some.name.startswith("CyclicType")
    assert fields == {"head": IntType()}

    @dataclass
    class Bar:
        data1: Optional[int]
        data2: Optional[int]

    t = TierkreisType.from_python(Bar)
    assert isinstance(t, StructType)
    fields = t.shape.content
    d1 = fields.pop("data1")
    assert isinstance(d1, VariantType)
    assert d1.shape.content.keys() == frozenset(
        [UnionTag.type_tag(int), UnionTag.none_type_tag()]
    )
    assert d1.shape.content[UnionTag.type_tag(int)] == IntType()
    assert fields == {"data2": d1}


@pytest.mark.xfail(raises=AssertionError)
def test_value_topython_list_with_empty():
    pyval = [[], [3, 4]]
    tkval = TierkreisValue.from_python(pyval)
    if tkval != VecValue([VecValue([]), VecValue([IntValue(3), IntValue(4)])]):
        # We expect this to work (even though xfail'd) - else test setup has gone wrong
        pytest.fail()
    pyval2 = tkval.try_autopython()
    # The following fails because we can't figure out the element-type of the outer list
    # from the first element (the empty list). Looking at the second element would work.
    assert pyval2 == pyval


@pytest.mark.xfail(raises=AssertionError)
def test_value_topython_map_with_empty():
    pyval = {10: [[], [3, 4]], 15: [[2.1, 3.2], []]}
    tkval = TierkreisValue.from_python(pyval)
    if tkval != MapValue(
        {
            IntValue(10): VecValue.from_iterable(
                (VecValue([]), VecValue([IntValue(3), IntValue(4)]))
            ),
            IntValue(15): VecValue.from_iterable(
                (VecValue([FloatValue(2.1), FloatValue(3.2)]), VecValue([]))
            ),
        }
    ):
        # We expect this to work (even though xfail'd) - else test setup has gone wrong
        pytest.fail()
    pyval2 = tkval.try_autopython()
    # The following fails because we can't figure out the value-type of the Map
    # from either element (whichever comes first!).
    # We'd need to combine type info from both values.
    assert pyval == pyval2


def test_inline_boxes():
    tg_box = TierkreisGraph()

    pair = tg_box.make_pair(tg_box.input["inp"], tg_box.add_const(3))
    tg_box.set_outputs(out=pair)

    def check_inlined(graph: TierkreisGraph) -> bool:
        return any(
            isinstance(node, FunctionNode) and node.function_name.name == "make_pair"
            for node in graph.nodes()
        )

    tg = TierkreisGraph()
    box = tg.add_box(tg_box, inp=tg.add_const("word"))
    tg.set_outputs(tg_out=box["out"])

    assert check_inlined(tg.inline_boxes())

    nested = TierkreisGraph()
    box2 = nested.add_box(tg)
    nested.set_outputs(nested_out=box2["tg_out"])

    assert not check_inlined(nested.inline_boxes())

    assert check_inlined(nested.inline_boxes(True))


# test of bugfix
def test_insert_graph_id():
    tg_box = TierkreisGraph()
    tg_box.set_outputs(a=tg_box.input["a"], b=tg_box.input["b"])

    tg = TierkreisGraph()
    con = tg.add_const("word")
    outs = tg.insert_graph(tg_box, a=con, b=tg.input["b"])
    tg.set_outputs(**outs)

    # before bugfix outs was empty

    assert outs == {"a": con, "b": tg.input["b"]}
