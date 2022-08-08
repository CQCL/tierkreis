from dataclasses import astuple
from pathlib import Path
from typing import Callable, Dict, Optional

import pytest

from tierkreis import TierkreisGraph
from tierkreis.core import Labels
from tierkreis.core.protos.tierkreis.graph import Graph
from tierkreis.core.types import (
    IntType,
    MapType,
    StringType,
    TierkreisTypeErrors,
    VecType,
)
from tierkreis.core.values import (
    BoolValue,
    FloatValue,
    IntValue,
    StringValue,
    StructValue,
    TierkreisValue,
    VariantValue,
    VecValue,
)
from tierkreis.frontend.runtime_client import RuntimeClient
from tierkreis.frontend.tksl import load_tksl_file


def _auto_name_map(index_map: dict[int, int]) -> dict[str, str]:
    return {f"NewNode({key})": f"NewNode({val})" for key, val in index_map.items()}


def _compare_graphs(
    first: TierkreisGraph,
    second: TierkreisGraph,
    node_map: Optional[dict[str, str]] = None,
) -> None:
    f_proto = first.to_proto()
    s_proto = second.to_proto()
    if node_map:
        new_nodes = {
            node_map.get(name, name): node for name, node in s_proto.nodes.items()
        }
        new_edges = []
        for edge in s_proto.edges:
            edge.node_from = node_map.get(edge.node_from, edge.node_from)
            edge.node_to = node_map.get(edge.node_to, edge.node_to)
            new_edges.append(edge)
        s_proto = Graph(new_nodes, new_edges)
    assert f_proto.nodes == s_proto.nodes
    # jsonify type annotations for ease of comparison
    for proto in (f_proto, s_proto):
        for e in proto.edges:
            if e.edge_type is not None:
                # hack, edge_type should be a TierkreisType
                # but we are converting to string for compairson
                e.edge_type = e.edge_type.to_json()  # type: ignore
    edge_set = lambda edge_list: set(map(astuple, edge_list))
    assert edge_set(f_proto.edges) == edge_set(s_proto.edges)


def _vecs_graph() -> TierkreisGraph:
    tg = TierkreisGraph()
    con = tg.add_const([2, 4])
    tg.set_outputs(vec=con)
    tg.annotate_output("vec", VecType(IntType()))

    return tg


def _structs_graph() -> TierkreisGraph:
    tg = TierkreisGraph()
    sturct = tg.add_func("builtin/make_struct", name="hello", age=23, height=12.3)
    sturct = tg.add_func("builtin/unpack_struct", struct=sturct["struct"])

    tg.set_outputs(age=sturct["age"])
    tg.annotate_output("age", IntType())
    return tg


def _maps_graph() -> TierkreisGraph:
    tg = TierkreisGraph()
    mp_val = tg.add_func("builtin/remove_key", map=tg.input["mp"], key=3)
    ins = tg.add_func("builtin/insert_key", map=mp_val["map"], key=5, val="bar")

    tg.set_outputs(mp=ins["map"], vl=mp_val["val"])
    tg.annotate_input("mp", MapType(IntType(), StringType()))
    tg.annotate_output("mp", MapType(IntType(), StringType()))
    tg.annotate_output("vl", StringType())

    return tg


def _tag_match_graph() -> TierkreisGraph:
    id_graph = TierkreisGraph()
    id_graph.set_outputs(value=id_graph.input[Labels.VALUE])

    tg = TierkreisGraph()
    in_v = tg.add_tag("foo", value=4)
    m = tg.add_match(in_v, foo=tg.add_const(id_graph))
    e = tg.add_func("builtin/eval", thunk=m[Labels.THUNK])
    tg.set_outputs(res=e[Labels.VALUE])
    tg.annotate_output("res", IntType())

    return tg


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "source,expected_gen,rename_map",
    [
        ("vecs", _vecs_graph, {}),
        ("structs", _structs_graph, {1: 0, 2: 1, 3: 2, 0: 3}),
        ("maps", _maps_graph, {0: 1, 1: 0, 2: 4, 4: 3, 3: 2}),
        ("tag_match", _tag_match_graph, {0: 1, 1: 0, 2: 3, 3: 2}),
    ],
)
async def test_parse_sample(
    source: str,
    expected_gen: Callable[[], TierkreisGraph],
    rename_map: dict[int, int],
    client: RuntimeClient,
) -> None:
    sig = await client.get_signature()

    tg = load_tksl_file(
        Path(__file__).parent / f"tksl_samples/{source}.tksl", signature=sig
    )

    _compare_graphs(tg, expected_gen(), _auto_name_map(rename_map))

    tg = await client.type_check_graph(tg)


@pytest.mark.asyncio
async def test_parse_bigexample(client: RuntimeClient) -> None:
    sig = await client.get_signature()

    tg = load_tksl_file(
        Path(__file__).parent / "tksl_samples/antlr_sample.tksl",
        signature=sig,
        function_name="func",
    )

    tg = await client.type_check_graph(tg)
    assert len(tg.nodes()) == 23

    for flag in (True, False):
        outputs = await client.run_graph(tg, {"v1": 67, "v2": (45, flag)})

        pyouts = {key: val.try_autopython() for key, val in outputs.items()}
        assert pyouts == {"o2": 103, "o1": 536 + (2 if flag else 5)}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "source,inputs,expected_outputs",
    [
        ("option.tksl", {}, {"some": IntValue(30), "none": IntValue(-1)}),
        ("pair.tksl", {}, {"first": IntValue(2), "second": StringValue("asdf")}),
        ("if_no_inputs.tksl", {"pred": BoolValue(True)}, {"res": IntValue(3)}),
        ("if_no_inputs.tksl", {"pred": BoolValue(False)}, {"res": IntValue(5)}),
        (
            "match_variant.tksl",
            {"expr": VariantValue("cst", IntValue(5)), "vv": IntValue(67)},
            {"res": IntValue(5)},
        ),
        (
            "match_variant.tksl",
            {"expr": VariantValue("var", StructValue({})), "vv": IntValue(4)},
            {"res": IntValue(4)},
        ),
        (
            "match_variant.tksl",
            {
                "expr": VariantValue(
                    "sum", StructValue({"a": IntValue(5), "b": IntValue(3)})
                ),
                "vv": IntValue(99),
            },
            {"res": IntValue(8)},
        ),
        (
            "match_variant.tksl",
            {
                "expr": VariantValue(
                    "prod", StructValue({"a": IntValue(5), "b": IntValue(3)})
                ),
                "vv": IntValue(99),
            },
            {"res": IntValue(15)},
        ),
    ],
)
async def test_run_sample(
    client: RuntimeClient,
    source: str,
    inputs: Dict[str, TierkreisValue],
    expected_outputs: Dict[str, TierkreisValue],
) -> None:
    sig = await client.get_signature()

    tg = load_tksl_file(Path(__file__).parent / "tksl_samples" / source, signature=sig)

    outputs = await client.run_graph(tg, inputs)
    assert outputs == expected_outputs


@pytest.mark.asyncio
async def test_arithmetic(client: RuntimeClient) -> None:
    sig = await client.get_signature()

    tg = load_tksl_file(
        Path(__file__).parent / "tksl_samples/arithmetic.tksl", signature=sig
    )

    outputs = await client.run_graph(tg, {})
    # each output should result in a logically true result
    assert all(val.try_autopython() for val in outputs.values())


@pytest.mark.asyncio
async def test_higher_order(client: RuntimeClient) -> None:
    sig = await client.get_signature()

    meat = load_tksl_file(
        Path(__file__).parent / "tksl_samples/sandwich.tksl",
        signature=sig,
        function_name="meat",
    )

    meta_sandwich = load_tksl_file(
        Path(__file__).parent / "tksl_samples/sandwich.tksl",
        signature=sig,
        function_name="meta_sandwich",
    )

    assert (await client.run_graph(meat, {"inp": 2.0}))["out"].try_autopython() == 4.0
    assert (await client.run_graph(meta_sandwich, {"inp": 1.5}))[
        "out"
    ].try_autopython() == 5.0


@pytest.mark.asyncio
async def test_bad_annotations(client: RuntimeClient) -> None:
    sig = await client.get_signature()

    tg = load_tksl_file(
        Path(__file__).parent / "tksl_samples/bad_annotate.tksl",
        signature=sig,
    )

    with pytest.raises(TierkreisTypeErrors) as err:
        await client.type_check_graph(tg)

    assert len(err.value) == 2


def test_parse_const() -> None:
    from tierkreis.frontend.tksl.parse_tksl import parse_const

    assert parse_const("2.0") == FloatValue(2.0)
    assert parse_const("2") == IntValue(2)
    assert parse_const("-2.0") == FloatValue(-2.0)
    assert parse_const("[2,4]") == VecValue([IntValue(2), IntValue(4)])
    assert parse_const("[2.0,3.4]") == VecValue([FloatValue(2.0), FloatValue(3.4)])
    assert parse_const("[-2.0,-3.4]") == VecValue([FloatValue(-2.0), FloatValue(-3.4)])
    assert parse_const("tag(foo: 3)") == VariantValue("foo", IntValue(3))
