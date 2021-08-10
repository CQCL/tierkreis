# pylint: disable=redefined-outer-name, missing-docstring, invalid-name
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple, Type

import pytest
from pytket import Circuit  # type: ignore
from pytket.passes import FullPeepholeOptimise  # type: ignore
from tierkreis.core import TierkreisGraph
from tierkreis.core.tierkreis_graph import FunctionNode, NodePort
from tierkreis.core.tierkreis_struct import TierkreisStruct
from tierkreis.core.values import ArrayValue, CircuitValue, TierkreisValue
from tierkreis.core.types import IntType
from tierkreis.frontend.runtime_client import RuntimeClient


@pytest.fixture(scope="module")
def client() -> RuntimeClient:
    return RuntimeClient()


def nint_adder(number: int, client: RuntimeClient) -> TierkreisGraph:
    sig = client.signature

    with client.build_graph() as tk_g:
        current_outputs = tk_g.array_n_elements(tk_g.input.out.array, number)

        while len(current_outputs) > 1:
            next_outputs = []
            n_even = len(current_outputs) & ~1

            for i in range(0, n_even, 2):
                nod = tk_g.add_node(
                    sig["python_nodes"]["add"],
                    a=current_outputs[i],
                    b=current_outputs[i + 1],
                )
                next_outputs.append(nod.out.value)
            if len(current_outputs) > n_even:
                nod = tk_g.add_node(
                    sig["python_nodes"]["add"],
                    a=next_outputs[-1],
                    b=current_outputs[n_even],
                )
                next_outputs[-1] = nod.out.value
            current_outputs = next_outputs

        tk_g.set_outputs(out=current_outputs[0])

    return tk_g


def test_nint_adder(client: RuntimeClient):
    for in_list in ([1] * 5, list(range(5))):
        tk_g = nint_adder(len(in_list), client)
        in_list_value = TierkreisValue.from_python(in_list)
        outputs = client.run_graph(tk_g, {"array": in_list_value})
        assert outputs["out"].to_python(int) == sum(in_list)


def add_n_graph(increment: int) -> TierkreisGraph:
    tk_g = TierkreisGraph()

    add_node = tk_g.add_node("python_nodes/add", a=increment, b=tk_g.input.out.number)
    tk_g.set_outputs(output=add_node)

    return tk_g


def test_switch(client: RuntimeClient):
    add_2_g = add_n_graph(2)
    add_3_g = add_n_graph(3)
    tk_g = TierkreisGraph()
    sig = client.signature

    switch = tk_g.add_node(
        sig["builtin"]["switch"],
        true=tk_g.add_const(add_2_g),
        false=tk_g.add_const(add_3_g),
        predicate=tk_g.input.out.flag,
    )

    eval_node = tk_g.add_node(
        sig["builtin"]["eval"], thunk=switch, number=tk_g.input.out.number
    )

    tk_g.set_outputs(out=eval_node.out.output)

    true_value = TierkreisValue.from_python(True)
    false_value = TierkreisValue.from_python(False)
    in_value = TierkreisValue.from_python(3)

    assert client.run_graph(tk_g, {"flag": true_value, "number": in_value}) == {
        "out": TierkreisValue.from_python(5)
    }
    assert client.run_graph(tk_g, {"flag": false_value, "number": in_value}) == {
        "out": TierkreisValue.from_python(6)
    }


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
        client.signature["python_nodes"]["id_py"], value=tk_g.input.out.id_in
    )
    tk_g.set_outputs(id_out=id_node)

    return tk_g


def test_idpy(bell_circuit, client: RuntimeClient):
    def assert_id_py(val: Any, typ: Type) -> bool:
        val_encoded = TierkreisValue.from_python(val)
        tk_g = idpy_graph(client)
        output = client.run_graph(tk_g, {"id_in": val_encoded})
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
        assert assert_id_py(val, typ)


def test_compile_circuit(bell_circuit: Circuit, client: RuntimeClient) -> None:
    tg = TierkreisGraph()
    compile_node = tg.add_node(
        client.signature["pytket"]["compile_circuits"],
        circuits=tg.input.out.input,
        pass_name=tg.add_const("FullPeepholeOptimise"),
    )
    tg.set_outputs(out=compile_node)

    inp_circ = bell_circuit.copy()
    FullPeepholeOptimise().apply(bell_circuit)
    assert client.run_graph(tg, {"input": ArrayValue([CircuitValue(inp_circ)])}) == {
        "out": ArrayValue([CircuitValue(bell_circuit)])
    }


def test_execute_circuit(bell_circuit: Circuit, client: RuntimeClient) -> None:
    tg = TierkreisGraph()
    execute_node = tg.add_node(
        client.signature["pytket"]["execute"],
        circuit_shots=tg.input.out.input,
        backend_name=tg.add_const("AerBackend"),
    )
    tg.set_outputs(out=execute_node)

    outputs = client.run_graph(
        tg,
        {"input": TierkreisValue.from_python([(bell_circuit, 10), (bell_circuit, 20)])},
    )["out"].to_python(List[Tuple[Dict[str, float], int]])

    assert outputs[0][1] == 10
    assert outputs[1][1] == 20


def test_interactive_infer(client: RuntimeClient) -> None:
    # test when built with client types are auto inferred
    with client.build_graph() as tg:
        _, val1 = tg.copy_value(3)
        tg.set_outputs(out=val1)

    assert any(node.is_delete_node() for node in tg.nodes().values())

    assert isinstance(tg.get_edge(val1, NodePort(tg.output, "out")).type_, IntType)


# TODO signature and typecheck tests
# TODO test Box
