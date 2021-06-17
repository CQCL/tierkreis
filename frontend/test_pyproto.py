from typing import Dict, List, Tuple, Type, Any
from dataclasses import dataclass
import pytest
from pytket import Circuit  # type: ignore
from tierkreis.frontend.proto_graph_builder import ProtoGraphBuilder
from tierkreis.core.values import TierkreisValue, TierkreisStruct
from tierkreis.frontend.run_graph import run_graph


def nint_adder(n: int) -> ProtoGraphBuilder:
    gb = ProtoGraphBuilder()

    # c_node = gb.add_node("const1", "const", {"value": 67})
    unp_node = gb.add_node("unp", "builtin/unpack_array")
    # gb.add_edge((c_node, "out"), (add_node, "rhs"))
    add_node0 = gb.add_node("add0", "python_nodes/add")
    gb.add_edge((unp_node, "0"), (add_node0, "a"), int)
    gb.add_edge((unp_node, "1"), (add_node0, "b"), int)
    add_nodes = [add_node0]

    for i in range(1, n - 1):
        n_nod = gb.add_node(f"add{i}", "python_nodes/add")
        gb.add_edge((add_nodes[i - 1], "c"), (n_nod, "a"), int)
        gb.add_edge((unp_node, f"{i+1}"), (n_nod, "b"), int)
        add_nodes.append(n_nod)

    gb.register_input("in", List[int], (unp_node, "array"))
    gb.register_output("out", int, (add_nodes[-1], "c"))

    return gb


def add_n_graph(n: int) -> ProtoGraphBuilder:
    gb = ProtoGraphBuilder()
    const_node = gb.add_const("increment", n)
    add_node = gb.add_node("add", "python_nodes/add")
    gb.add_edge((const_node, "value"), (add_node, "a"), int)

    gb.register_input("in", int, (add_node, "b"))
    gb.register_output("out", int, (add_node, "c"))

    return gb


def test_nint_adder():
    for in_list in ([1] * 5, list(range(5))):
        gb = nint_adder(len(in_list))
        in_list_value = TierkreisValue.from_python(in_list)
        outputs = run_graph(gb, {"in": in_list_value})
        assert TierkreisValue.to_python(outputs["out"], int) == sum(in_list)


def test_switch():
    add_2_g = add_n_graph(2)
    add_3_g = add_n_graph(3)
    gb = ProtoGraphBuilder()

    true_thunk = gb.add_const("true_thunk", add_2_g.graph)
    false_thunk = gb.add_const("false_thunk", add_3_g.graph)

    switch = gb.add_node("switch", "builtin/switch")
    gb.add_edge((true_thunk, "value"), (switch, "true"), add_2_g.get_type())
    gb.add_edge((false_thunk, "value"), (switch, "false"), add_3_g.get_type())

    eval_node = gb.add_node("eval", "builtin/eval")
    gb.add_edge((switch, "value"), (eval_node, "thunk"), add_2_g.get_type())

    gb.register_input("in", int, (eval_node, "in"))
    gb.register_input("flag", bool, (switch, "predicate"))
    gb.register_output("out", int, (eval_node, "out"))

    true_value = TierkreisValue.from_python(True)
    false_value = TierkreisValue.from_python(True)
    in_value = TierkreisValue.from_python(3)

    assert run_graph(gb, {"flag": true_value, "in": in_value}) == {
        "out": TierkreisValue.from_python(5)
    }
    assert run_graph(gb, {"flag": false_value, "in": in_value}) == {
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


def idpy_graph(typ: Type) -> ProtoGraphBuilder:
    gb = ProtoGraphBuilder()
    id_node = gb.add_node("id_py", "python_nodes/id_py")

    gb.register_input("id_in", typ, (id_node, "value"))
    gb.register_output("id_out", typ, (id_node, "value"))

    return gb


def test_idpy(bell_circuit):
    def assert_id_py(val: Any, typ: Type) -> bool:
        val_encoded = TierkreisValue.from_python(val)
        gb = idpy_graph(typ)
        output = run_graph(gb, {"id_in": val_encoded})
        val_decoded = TierkreisValue.to_python(output["id_out"], typ)
        return val_decoded == val

    dic: Dict[int, bool] = {1: True, 2: False}

    nestst = NestedStruct([1, 2, 3], (5, True))
    testst = TstStruct(2, False, Circuit(1), {66: 77}, nestst)
    for val, typ in [
        (bell_circuit, Circuit),
        (dic, Dict[int, bool]),
        (testst, TstStruct),
        ("test123", str),
    ]:
        assert assert_id_py(val, typ)


def test_compile_circuit(bell_circuit):
    gb = ProtoGraphBuilder()
    id_node = gb.add_node("compile", "python_nodes/compile_circuit")

    gb.register_input("in", Circuit, (id_node, "circuit"))
    gb.register_output("out", Circuit, (id_node, "compiled_circuit"))
    from pytket.passes import FullPeepholeOptimise  # type: ignore

    inp_circ = bell_circuit.copy()
    FullPeepholeOptimise().apply(bell_circuit)
    assert run_graph(gb, {"in": inp_circ}) == {"out": bell_circuit}
