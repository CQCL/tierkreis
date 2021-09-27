# pylint: disable=redefined-outer-name, missing-docstring, invalid-name
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterator, List, Tuple, Type

import pytest
from pytket import Circuit  # type: ignore
from pytket.passes import FullPeepholeOptimise  # type: ignore
from tierkreis import TierkreisGraph
from tierkreis.core.function import TierkreisFunction
from tierkreis.frontend import RuntimeClient, local_runtime, docker_runtime
from tierkreis.core.tierkreis_graph import FunctionNode, NodePort
from tierkreis.core.tierkreis_struct import TierkreisStruct
from tierkreis.core.types import IntType, TierkreisTypeErrors
from tierkreis.core.values import VecValue, CircuitValue, TierkreisValue


@pytest.fixture(scope="module")
def client(request) -> Iterator[RuntimeClient]:
    # yield RuntimeClient("https://cloud.cambridgequantum.com/tierkreis/v1")
    if request.config.getoption("--docker"):
        # launch docker container and close at end
        with docker_runtime(
            "cqc/tierkreis",
            show_output=True,
        ) as local_client:
            yield local_client
    else:
        exe = Path("../target/debug/tierkreis-server")
        # launch a local server for this test run and kill it at the end
        with local_runtime(exe, show_output=True) as local_client:
            yield local_client


def nint_adder(number: int, client: RuntimeClient) -> TierkreisGraph:
    sig = client.signature

    with client.build_graph() as tk_g:
        current_outputs = tk_g.vec_last_n_elems(tk_g.input["array"], number)

        while len(current_outputs) > 1:
            next_outputs = []
            n_even = len(current_outputs) & ~1

            for i in range(0, n_even, 2):
                nod = tk_g.add_node(
                    sig["python_nodes"]["add"],
                    a=current_outputs[i],
                    b=current_outputs[i + 1],
                )
                next_outputs.append(nod["value"])
            if len(current_outputs) > n_even:
                nod = tk_g.add_node(
                    sig["python_nodes"]["add"],
                    a=next_outputs[-1],
                    b=current_outputs[n_even],
                )
                next_outputs[-1] = nod["value"]
            current_outputs = next_outputs

        tk_g.set_outputs(out=current_outputs[0])

    return tk_g


@pytest.mark.asyncio
async def test_nint_adder(client: RuntimeClient):
    for in_list in ([1] * 5, list(range(5))):
        tk_g = nint_adder(len(in_list), client)
        in_list_value = TierkreisValue.from_python(in_list)
        outputs = await client.run_graph(tk_g, {"array": in_list_value})
        assert outputs["out"].to_python(int) == sum(in_list)


def add_n_graph(increment: int) -> TierkreisGraph:
    tk_g = TierkreisGraph()

    add_node = tk_g.add_node("python_nodes/add", a=increment, b=tk_g.input["number"])
    tk_g.set_outputs(output=add_node)

    return tk_g


@pytest.mark.asyncio
async def test_switch(client: RuntimeClient):
    add_2_g = add_n_graph(2)
    add_3_g = add_n_graph(3)
    tk_g = TierkreisGraph()
    sig = client.signature

    switch = tk_g.add_node(
        sig["builtin"]["switch"],
        if_true=tk_g.add_const(add_2_g),
        if_false=tk_g.add_const(add_3_g),
        pred=tk_g.input["flag"],
    )

    eval_node = tk_g.add_node(
        sig["builtin"]["eval"], thunk=switch, number=tk_g.input["number"]
    )

    tk_g.set_outputs(out=eval_node["output"])

    outs = await client.run_graph(tk_g, {"flag": True, "number": 3})

    assert outs["out"].try_autopython() == 5
    outs = await client.run_graph(tk_g, {"flag": False, "number": 3})

    assert outs["out"].try_autopython() == 6


@pytest.fixture
def bell_circuit() -> Circuit:
    return Circuit(2).H(0).CX(0, 1).measure_all()


@dataclass
class NestedStruct(TierkreisStruct):
    s: List[int]
    a: Tuple[int, bool]


@dataclass
class TstStruct(TierkreisStruct):
    x: int
    y: bool
    c: Circuit
    m: Dict[int, int]
    n: NestedStruct


def idpy_graph(client: RuntimeClient) -> TierkreisGraph:
    tk_g = TierkreisGraph()
    id_node = tk_g.add_node(
        client.signature["python_nodes"]["id_py"], value=tk_g.input["id_in"]
    )
    tk_g.set_outputs(id_out=id_node)

    return tk_g


@pytest.mark.asyncio
async def test_idpy(bell_circuit, client: RuntimeClient):
    async def assert_id_py(val: Any, typ: Type) -> bool:
        tk_g = idpy_graph(client)
        output = await client.run_graph(tk_g, {"id_in": val})
        val_decoded = output["id_out"].to_python(typ)
        return val_decoded == val

    dic: Dict[int, bool] = {1: True, 2: False}

    nestst = NestedStruct([1, 2, 3], (5, True))
    testst = TstStruct(2, False, Circuit(1), {66: 77}, nestst)
    for val, typ in [
        (bell_circuit, Circuit),
        (dic, Dict[int, bool]),
        (testst, TstStruct),
        ("test123", str),
        (2, int),
        (132.3, float),
        ((2, "a"), Tuple[int, str]),
        ([1, 2, 3], List[int]),
        (True, bool),
    ]:
        assert await assert_id_py(val, typ)


@pytest.mark.asyncio
async def test_compile_circuit(bell_circuit: Circuit, client: RuntimeClient) -> None:
    tg = TierkreisGraph()
    compile_node = tg.add_node(
        client.signature["pytket"]["compile_circuits"],
        circuits=tg.input["input"],
        pass_name=tg.add_const("FullPeepholeOptimise"),
    )
    tg.set_outputs(out=compile_node)

    inp_circ = bell_circuit.copy()
    FullPeepholeOptimise().apply(bell_circuit)
    assert await client.run_graph(tg, {"input": [inp_circ]}) == {
        "out": VecValue([CircuitValue(bell_circuit)])
    }


@pytest.mark.asyncio
async def test_execute_circuit(bell_circuit: Circuit, client: RuntimeClient) -> None:
    tg = TierkreisGraph()
    execute_node = tg.add_node(
        client.signature["pytket"]["execute"],
        circuit_shots=tg.input["input"],
        backend_name=tg.add_const("AerBackend"),
    )
    tg.set_outputs(out=execute_node)

    outputs = (
        await client.run_graph(
            tg,
            {"input": [(bell_circuit, 10), (bell_circuit, 20)]},
        )
    )["out"].to_python(List[Tuple[Dict[str, float], int]])

    assert outputs[0][1] == 10
    assert outputs[1][1] == 20


@pytest.mark.asyncio
async def test_interactive_infer(client: RuntimeClient) -> None:
    # test when built with client types are auto inferred
    with client.build_graph() as tg:
        _, val1 = tg.copy_value(3)
        tg.set_outputs(out=val1)

    assert any(node.is_discard_node() for node in tg.nodes().values())

    assert isinstance(tg.get_edge(val1, NodePort(tg.output, "out")).type_, IntType)


@pytest.mark.asyncio
async def test_infer_errors(client: RuntimeClient) -> None:
    # build graph with two type errors
    tg = TierkreisGraph()
    node_0 = tg.add_const(0)
    node_1 = tg.add_const(1)
    tg.add_edge(node_0["value"], tg.input["illegal"])
    tg.set_outputs(out=node_1["invalid"])

    with pytest.raises(TierkreisTypeErrors) as err:
        await client.type_check_graph(tg)

    assert len(err.value) == 2


@pytest.mark.asyncio
async def test_infer_errors_when_running(client: RuntimeClient) -> None:
    # build graph with two type errors
    tg = TierkreisGraph()
    node_0 = tg.add_const(0)
    node_1 = tg.add_const(1)
    tg.add_edge(node_0["value"], tg.input["illegal"])
    tg.set_outputs(out=node_1["invalid"])

    with pytest.raises(TierkreisTypeErrors) as err:
        await client.run_graph(tg, {})

    assert len(err.value) == 2


@pytest.mark.asyncio
async def test_fail_node(client: RuntimeClient) -> None:
    tg = TierkreisGraph()
    tg.add_node("python_nodes/fail")

    with pytest.raises(RuntimeError) as err:
        await client.run_graph(tg, {})

    assert "fail node was run" in str(err.value)


def graph_from_func(func: TierkreisFunction) -> TierkreisGraph:
    # build a graph with a single function node, with the same interface as that
    # function
    tg = TierkreisGraph()
    node = tg.add_node(func.name, **{port: tg.input[port] for port in func.input_order})
    tg.set_outputs(**{port: node[port] for port in func.output_order})
    return tg


@pytest.mark.asyncio
async def test_vec_sequence(client: RuntimeClient) -> None:
    pop_g = graph_from_func(client.signature["builtin"]["pop"])
    push_g = graph_from_func(client.signature["builtin"]["push"])

    seq_g = graph_from_func(client.signature["builtin"]["sequence"])

    outputs = await client.run_graph(seq_g, {"first": pop_g, "second": push_g})

    sequenced_g = outputs["sequenced"].to_python(TierkreisGraph).inline_boxes()

    # check composition is succesful
    functions = {
        node.function_name
        for node in sequenced_g.nodes().values()
        if isinstance(node, FunctionNode)
    }
    assert {"builtin/push", "builtin/pop"}.issubset(functions)

    # check composition evaluates
    vec_in = ["foo", "bar", "bang"]
    out = await client.run_graph(sequenced_g, {"vec": vec_in})
    vec_out = out["vec"].to_python(List[str])
    assert vec_in == vec_out
