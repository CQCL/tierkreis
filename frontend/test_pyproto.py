from typing import Dict, List, Tuple
from dataclasses import dataclass
import pytest
from pytket import Circuit
from tierkreis.frontend.proto_graph_builder import ProtoGraphBuilder
from tierkreis.core import TKStruct
from tierkreis.frontend.run_graph import run_graph


def nint_adder(n: int) -> ProtoGraphBuilder:
    gb = ProtoGraphBuilder()

    # c_node = gb.add_node("const1", "const", {"value": 67})
    unp_node = gb.add_node("unp", "builtin/unpack_array")
    # gb.add_edge((c_node, "out"), (add_node, "rhs"))
    add_node0 = gb.add_node("add0", "add")
    gb.add_edge((unp_node, "0"), (add_node0, "lhs"), int)
    gb.add_edge((unp_node, "1"), (add_node0, "rhs"), int)
    add_nodes = [add_node0]

    for i in range(1, n - 1):
        n_nod = gb.add_node(f"add{i}", "add")
        gb.add_edge((add_nodes[i - 1], "out"), (n_nod, "lhs"), int)
        gb.add_edge((unp_node, f"{i+1}"), (n_nod, "rhs"), int)
        add_nodes.append(n_nod)

    gb.register_input("in", List[int], (unp_node, "array"))
    gb.register_output("out", int, (add_nodes[-1], "out"))

    return gb


def add_n_graph(n: int) -> ProtoGraphBuilder:
    gb = ProtoGraphBuilder()
    const_node = gb.add_const("increment", n)
    add_node = gb.add_node("add", "add")
    gb.add_edge((const_node, "out"), (add_node, "lhs"), int)

    gb.register_input("in", int, (add_node, "rhs"))
    gb.register_output("out", int, (add_node, "out"))

    return gb


def test_nint_adder():
    for in_list in ([1] * 5, list(range(5))):
        gb = nint_adder(len(in_list))
        assert run_graph(gb, {"in": in_list}) == {"out": sum(in_list)}


def test_switch():
    add_2_g = add_n_graph(2)
    add_3_g = add_n_graph(3)
    gb = ProtoGraphBuilder()

    true_thunk = gb.add_const("true_thunk", add_2_g.graph)
    false_thunk = gb.add_const("false_thunk", add_3_g.graph)

    switch = gb.add_node("switch", "builtin/switch")
    gb.add_edge((true_thunk, "out"), (switch, "true"), add_2_g.get_type())
    gb.add_edge((false_thunk, "out"), (switch, "false"), add_3_g.get_type())

    eval_node = gb.add_node("eval", "builtin/eval")
    gb.add_edge((switch, "out"), (eval_node, "thunk"), add_2_g.get_type())

    gb.register_input("in", int, (eval_node, "in"))
    gb.register_input("flag", bool, (switch, "predicate"))
    gb.register_output("out", int, (eval_node, "out"))

    assert run_graph(gb, {"flag": True, "in": 3}) == {"out": 5}
    assert run_graph(gb, {"flag": False, "in": 3}) == {"out": 6}


@pytest.fixture
def bell_circuit() -> Circuit:
    return Circuit(2).H(0).CX(0, 1).measure_all()


def test_circuit_idpy(bell_circuit):
    gb = ProtoGraphBuilder()
    id_node = gb.add_node("id_py", "id_py")

    gb.register_input("id_in", Circuit, (id_node, "in"))
    gb.register_output("id_out", Circuit, (id_node, "out"))

    assert run_graph(gb, {"id_in": bell_circuit}) == {"id_out": bell_circuit}


def test_dictionary_idpy():
    gb = ProtoGraphBuilder()
    id_node = gb.add_node("id", "id_py")

    gb.register_input("in", Dict[int, bool], (id_node, "in"))
    gb.register_output("out", Dict[int, bool], (id_node, "out"))

    dic: Dict[int, bool] = {1: True, 2: False}
    assert run_graph(gb, {"in": dic}) == {"out": dic}


@dataclass
class NestedStruct(TKStruct):
    s: List[int]
    a: Tuple[int, bool]


@dataclass
class TestStruct(TKStruct):
    x: int
    y: bool
    c: Circuit
    m: Dict[int, int]
    n: NestedStruct


def test_struct_idpy():
    gb = ProtoGraphBuilder()
    id_node = gb.add_node("id", "id_py")

    gb.register_input("in", TestStruct, (id_node, "in"))
    gb.register_output("out", TestStruct, (id_node, "out"))

    nestst = NestedStruct([1, 2, 3], (5, True))
    testst = TestStruct(2, False, Circuit(1), {66: 77}, nestst)

    assert run_graph(gb, {"in": testst}) == {"out": testst}


def test_compile_circuit(bell_circuit):
    gb = ProtoGraphBuilder()
    id_node = gb.add_node("compile", "compile_circuit")

    gb.register_input("in", Circuit, (id_node, "circuit"))
    gb.register_output("out", Circuit, (id_node, "compiled_circuit"))
    from pytket.passes import FullPeepholeOptimise

    inp_circ = bell_circuit.copy()
    FullPeepholeOptimise().apply(bell_circuit)
    assert run_graph(gb, {"in": inp_circ}) == {"out": bell_circuit}
