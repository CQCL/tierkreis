from typing import Optional, Union, Callable
from dataclasses import astuple
from pathlib import Path
import pytest

from tierkreis.frontend import RuntimeClient
from tierkreis.frontend.tksl import parse_tksl
from tierkreis import TierkreisGraph
from tierkreis.core.protos.tierkreis.graph import Graph


def _get_source(path: Union[str, Path]) -> str:
    with open(path) as f:
        return f.read()


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
    edge_set = lambda edge_list: set(map(astuple, edge_list))
    assert edge_set(f_proto.edges) == edge_set(s_proto.edges)


def _vecs_graph() -> TierkreisGraph:
    tg = TierkreisGraph()
    con = tg.add_const([2, 4])
    tg.set_outputs(vec=con)
    return tg


def _structs_graph() -> TierkreisGraph:
    tg = TierkreisGraph()
    sturct = tg.add_node("builtin/make_struct", name="hello", age=23, height=12.3)
    sturct = tg.add_node("builtin/unpack_struct", struct=sturct["struct"])

    tg.set_outputs(age=sturct["age"])

    return tg


def _maps_graph() -> TierkreisGraph:
    tg = TierkreisGraph()
    mp_val = tg.add_node("builtin/remove_key", map=tg.input["mp"], key=3)
    ins = tg.add_node("builtin/insert_key", map=mp_val["map"], key=5, val="bar")

    tg.set_outputs(mp=ins["map"], vl=mp_val["val"])

    return tg


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "source,expected_gen,rename_map",
    [
        ("vecs", _vecs_graph, {}),
        ("structs", _structs_graph, {1: 0, 2: 1, 3: 2, 0: 3}),
        ("maps", _maps_graph, {0: 1, 1: 0, 2: 4, 4: 3, 3: 2}),
    ],
)
async def test_parse_sample(
    source: str,
    expected_gen: Callable[[], TierkreisGraph],
    rename_map: dict[int, int],
    client: RuntimeClient,
) -> None:
    sig = await client.get_signature()

    tg = parse_tksl(
        _get_source(Path(__file__).parent / f"tksl_samples/{source}.tksl"), sig
    )

    _compare_graphs(tg, expected_gen(), _auto_name_map(rename_map))

    tg = await client.type_check_graph(tg)


@pytest.mark.asyncio
async def test_parse_bigexample(client: RuntimeClient) -> None:
    sig = await client.get_signature()

    tg = parse_tksl(
        _get_source(Path(__file__).parent / "tksl_samples/antlr_sample.tksl"), sig
    )

    tg = await client.type_check_graph(tg)
    assert len(tg.nodes()) == 24

    for flag in (True, False):
        outputs = await client.run_graph(tg, {"v1": 67, "v2": (45, flag)})

        pyouts = {key: val.try_autopython() for key, val in outputs.items()}
        assert pyouts == {"o2": 103, "o1": 536 + (2 if flag else 5)}


@pytest.mark.asyncio
async def test_parse_runcircuit(client: RuntimeClient) -> None:
    sig = await client.get_signature()

    tg = parse_tksl(
        _get_source(Path(__file__).parent / "tksl_samples/run_circuit.tksl"), sig
    )

    tg = await client.type_check_graph(tg)
    assert len(tg.nodes()) == 15
