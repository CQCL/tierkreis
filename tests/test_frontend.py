from dataclasses import dataclass
from time import time
from typing import Any, Dict, List, Optional, Tuple, Type

import pytest
from utils import nint_adder

from tierkreis import TierkreisGraph
from tierkreis.client import RuntimeClient
from tierkreis.core.graphviz import _merge_copies
from tierkreis.core.tierkreis_graph import FunctionNode
from tierkreis.core.utils import graph_from_func
from tierkreis.core.values import FloatValue, VariantValue
from tierkreis.pyruntime import PyRuntime
from tierkreis.worker.exceptions import NodeExecutionError


@pytest.mark.asyncio
async def test_nint_adder(client: RuntimeClient):
    for in_list in ([1] * 5, list(range(5))):
        tk_g = nint_adder(len(in_list))
        outputs = await client.run_graph(tk_g, array=in_list)
        assert outputs["out"].try_autopython() == sum(in_list)


def add_n_graph(increment: int) -> TierkreisGraph:
    tk_g = TierkreisGraph()

    add_func = tk_g.add_func(
        "iadd", a=tk_g.add_const(increment), b=tk_g.input["number"]
    )
    tk_g.set_outputs(output=add_func)

    return tk_g


@pytest.mark.asyncio
async def test_switch(client: RuntimeClient):
    add_2_g = add_n_graph(2)
    add_3_g = add_n_graph(3)
    tk_g = TierkreisGraph()

    switch = tk_g.add_func(
        "switch",
        if_true=tk_g.add_const(add_2_g),
        if_false=tk_g.add_const(add_3_g),
        pred=tk_g.input["flag"],
    )

    eval_node = tk_g.add_func("eval", thunk=switch, number=tk_g.input["number"])

    tk_g.set_outputs(out=eval_node["output"])

    outs = await client.run_graph(tk_g, flag=True, number=3)

    assert outs["out"].try_autopython() == 5
    outs = await client.run_graph(tk_g, flag=False, number=3)

    assert outs["out"].try_autopython() == 6


@pytest.mark.asyncio
async def test_match(client: RuntimeClient):
    # Test a variant type < one: Float | many: Vec<Float> >
    one_graph = TierkreisGraph()
    one_graph.set_outputs(
        value=one_graph.add_func(
            "fadd", a=one_graph.input["value"], b=one_graph.add_const(3.14)
        )
    )
    many_graph = TierkreisGraph()
    many_graph.set_outputs(
        value=many_graph.add_func("pop", vec=many_graph.input["value"])["item"]
    )

    match_graph = TierkreisGraph()
    match_graph.set_outputs(
        result=match_graph.add_func(
            "python_nodes::id_delay",
            wait=match_graph.add_const(1),
            value=match_graph.add_func(
                "eval",
                thunk=match_graph.add_match(
                    match_graph.input["vv"],
                    one=match_graph.add_const(one_graph),
                    many=match_graph.add_func(
                        "python_nodes::id_delay",
                        wait=match_graph.add_const(1),
                        value=match_graph.add_const(many_graph),
                    ),
                )["thunk"],
            ),
        )
    )

    start_time = time()
    outs = await client.run_graph(match_graph, vv=VariantValue("one", FloatValue(6.0)))
    time_taken = time() - start_time
    assert outs["result"] == FloatValue(9.14)
    # Must have waited at least 1s for the delay on the graph output.
    assert time_taken >= 1.0

    if isinstance(client, PyRuntime):
        # PyRuntime waits for all inputs to a node to be ready.
        assert time_taken > 2.0
    else:
        # Should not have had to wait 1s first for the "many" graph input to be ready,
        # as that was not the variant was not selected.
        # (1.5s is arbitrary, but less than 2s.)
        assert time_taken < 1.5


@pytest.mark.asyncio
async def test_tag(client: RuntimeClient):
    g = TierkreisGraph()
    g.set_outputs(res=g.add_tag("foo", value=g.input["arg"]))
    v = FloatValue(67.1)
    outs = await client.run_graph(g, arg=v)
    assert outs == {"res": VariantValue("foo", v)}


@dataclass
class NestedStruct:
    s: List[int]
    a: Tuple[int, bool]
    b: Optional[str]
    d: Optional[float]


@dataclass
class TstStruct:
    x: int
    y: bool
    m: Dict[int, int]
    n: NestedStruct


@pytest.mark.asyncio
async def test_idpy(client: RuntimeClient, idpy_graph: TierkreisGraph):
    async def assert_id_py(val: Any, typ: Type) -> bool:
        output = await client.run_graph(idpy_graph, id_in=val)
        val_decoded = output["id_out"].to_python(typ)
        return val_decoded == val

    dic: Dict[int, bool] = {1: True, 2: False}

    nestst = NestedStruct([1, 2, 3], (5, True), "asdf", None)
    testst = TstStruct(2, False, {66: 77}, nestst)
    pairs: list[tuple[Any, Type]] = [
        (dic, dict[int, bool]),
        (testst, TstStruct),
        ("test123", str),
        (2, int),
        (132.3, float),
        ((2, "a"), tuple[int, str]),
        ([1, 2, 3], list[int]),
        (True, bool),
    ]
    for val, typ in pairs:
        assert await assert_id_py(val, typ)


@pytest.mark.asyncio
async def test_fail_node(client: RuntimeClient) -> None:
    tg = TierkreisGraph()
    tg.add_func("python_nodes::fail", value=tg.input["arg"])

    exception: Type[Exception] = (
        NodeExecutionError if isinstance(client, PyRuntime) else RuntimeError
    )
    with pytest.raises(exception) as err:
        await client.run_graph(tg, arg=3)

    assert "fail node was run" in str(err.value)


@pytest.mark.asyncio
async def test_vec_sequence(client: RuntimeClient) -> None:
    sig = await client.get_signature()
    pop_g = graph_from_func("pop", sig.root.functions["pop"])
    push_g = graph_from_func("push", sig.root.functions["push"])

    seq_g = graph_from_func("sequence", sig.root.functions["sequence"])

    outputs = await client.run_graph(seq_g, first=pop_g, second=push_g)

    sequenced_g: TierkreisGraph = (
        outputs["sequenced"].to_python(TierkreisGraph).inline_boxes()
    )

    # check composition is succesful
    functions = {
        node.function_name.name
        for node in sequenced_g.nodes()
        if isinstance(node, FunctionNode)
    }
    assert {"push", "pop"}.issubset(functions)

    # check composition evaluates
    vec_in = ["foo", "bar", "bang"]
    out = await client.run_graph(sequenced_g, vec=vec_in)
    vec_out = out["vec"].to_python(List[str])
    assert vec_in == vec_out


def test_merge_copies():
    tg = TierkreisGraph()
    x1, x2 = tg.copy_value(tg.input["x"])
    x3, x4 = tg.copy_value(x1)
    y1, y2 = tg.copy_value(x3)
    z1, z2 = tg.copy_value(x4)

    tg.set_outputs(x2=x2, y1=y1, y2=y2, z1=z1, z2=z2)

    assert tg.n_nodes == 6
    assert sum(1 for _ in tg.edges()) == 9

    tg = _merge_copies(tg)

    assert tg.n_nodes == 3
    assert sum(1 for _ in tg.edges()) == 6


@pytest.mark.asyncio
async def test_subspaces(client: RuntimeClient):
    tg = TierkreisGraph()
    idnode = tg.add_func("python_nodes::subspace::increment", value=tg.add_const(0))
    tg.set_outputs(out=idnode)

    assert (await client.run_graph(tg))["out"].try_autopython() == 2

    tg = TierkreisGraph()
    idnode = tg.add_func("python_nodes::increment", value=tg.add_const(0))
    tg.set_outputs(out=idnode)

    assert (await client.run_graph(tg))["out"].try_autopython() == 1


@pytest.mark.asyncio
async def test_map(client: RuntimeClient):
    thunk = TierkreisGraph()
    double = thunk.add_func("imul", a=thunk.input["value"], b=thunk.add_const(2))
    thunk.set_outputs(value=double)

    tg = TierkreisGraph()
    map_node = tg.add_func(
        "map", value=tg.add_const([1, 2, 3]), thunk=tg.add_const(thunk)
    )
    tg.set_outputs(value=map_node)

    assert (await client.run_graph(tg))["value"].try_autopython() == [2, 4, 6]
