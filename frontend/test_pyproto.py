# pylint: disable=redefined-outer-name, missing-docstring, invalid-name
import types
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple, Type

import pytest
from pytket import Circuit  # type: ignore
from pytket.passes import FullPeepholeOptimise  # type: ignore
from tierkreis.core import TierkreisGraph
from tierkreis.core.tierkreis_graph import NodePort, PortID
from tierkreis.core.tierkreis_struct import TierkreisStruct
from tierkreis.core.values import CircuitValue, TierkreisValue

from tierkreis.frontend.run_graph import run_graph, signature


@pytest.fixture(scope="module")
def sig() -> types.ModuleType:
    return signature()


def nint_adder(number: int, sig) -> TierkreisGraph:
    tk_g = TierkreisGraph()

    unp_node = tk_g.add_function_node(sig.builtin.unpack_array)
    current_outputs = [NodePort(unp_node, PortID(f"{i}")) for i in range(number)]

    while len(current_outputs) > 1:
        next_outputs = []
        n_even = len(current_outputs) & ~1

        for i in range(0, n_even, 2):
            nod = tk_g.add_function_node(sig.python_nodes.add)
            tk_g.add_edge(current_outputs[i], nod.in_port.a)
            tk_g.add_edge(current_outputs[i + 1], nod.in_port.b)
            next_outputs.append(nod.out_port.value)
        if len(current_outputs) > n_even:
            nod = tk_g.add_function_node(sig.python_nodes.add)
            tk_g.add_edge(next_outputs[-1], nod.in_port.a)
            tk_g.add_edge(current_outputs[n_even], nod.in_port.b)
            next_outputs[-1] = nod.out_port.value
        current_outputs = next_outputs

    tk_g.register_input("in", NodePort(unp_node, PortID("array")), int)
    tk_g.register_output("out", current_outputs[0])

    return tk_g


def test_nint_adder(sig):
    for in_list in ([1] * 5, list(range(5))):
        tk_g = nint_adder(len(in_list), sig)
        in_list_value = TierkreisValue.from_python(in_list)
        outputs = run_graph(tk_g.to_proto(), {"in": in_list_value})
        assert outputs["out"].to_python(int) == sum(in_list)


def add_n_graph(increment: int, sig) -> TierkreisGraph:
    tk_g = TierkreisGraph()
    tk_g.load_signature(sig)
    const_node = tk_g.add_const(increment)

    add_node = tk_g.add_function_node("python_nodes/add")
    tk_g.add_edge(const_node.out_port.value, add_node.in_port.a)

    tk_g.register_input("input", add_node.in_port.b)
    tk_g.register_output("output", add_node.out_port.value)

    return tk_g


def test_switch(sig):
    add_2_g = add_n_graph(2, sig)
    add_3_g = add_n_graph(3, sig)
    tk_g = TierkreisGraph()

    true_thunk = tk_g.add_const(add_2_g)
    false_thunk = tk_g.add_const(add_3_g)

    switch = tk_g.add_function_node(sig.builtin.switch)
    tk_g.add_edge(true_thunk.out_port.value, switch.in_port.true)
    tk_g.add_edge(false_thunk.out_port.value, switch.in_port.false)

    eval_node = tk_g.add_function_node(sig.builtin.eval)
    tk_g.add_edge(switch.out_port.value, eval_node.in_port.thunk)

    tk_g.register_input("in", eval_node.in_port.input, int)
    tk_g.register_input("flag", switch.in_port.predicate, bool)
    tk_g.register_output("out", eval_node.out_port.output, int)

    true_value = TierkreisValue.from_python(True)
    false_value = TierkreisValue.from_python(False)
    in_value = TierkreisValue.from_python(3)

    assert run_graph(tk_g.to_proto(), {"flag": true_value, "in": in_value}) == {
        "out": TierkreisValue.from_python(5)
    }
    assert run_graph(tk_g.to_proto(), {"flag": false_value, "in": in_value}) == {
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


def idpy_graph(typ: Type, sig) -> TierkreisGraph:
    tk_g = TierkreisGraph()
    id_node = tk_g.add_function_node(sig.python_nodes.id_py)

    tk_g.register_input("id_in", id_node.in_port.value, typ)
    tk_g.register_output("id_out", id_node.out_port.value, typ)

    return tk_g


def test_idpy(bell_circuit, sig):
    def assert_id_py(val: Any, typ: Type) -> bool:
        val_encoded = TierkreisValue.from_python(val)
        tk_g = idpy_graph(typ, sig)
        output = run_graph(tk_g.to_proto(), {"id_in": val_encoded})
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


def test_compile_circuit(bell_circuit, sig):
    tg = TierkreisGraph()
    compile_node = tg.add_function_node(sig.pytket.compile_circuit)

    tg.register_input("in", compile_node.in_port.circuit)
    tg.register_output("out", compile_node.out_port.value)

    inp_circ = bell_circuit.copy()
    FullPeepholeOptimise().apply(bell_circuit)
    assert run_graph(tg.to_proto(), {"in": CircuitValue(inp_circ)}) == {
        "out": CircuitValue(bell_circuit)
    }
