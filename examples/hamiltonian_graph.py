# /// script
# requires-python = ">=3.12"
# dependencies = ["tierkreis", "pytket"]
#
# [tool.uv.sources]
# tierkreis = { path = "../tierkreis", editable = true }
# ///
import json
from pathlib import Path
from uuid import UUID

from pytket._tket.unit_id import Qubit
from pytket.pauli import Pauli, QubitPauliString
from pytket._tket.circuit import Circuit, fresh_symbol
from tierkreis.controller import run_graph
from tierkreis.controller.data.graph import (
    Eval,
    GraphData,
    Const,
    Func,
    IfElse,
    Output,
    Input,
    Map,
    Loop,
)
from tierkreis.controller.data.location import Loc
from tierkreis.controller.executor.multiple import MultipleExecutor
from tierkreis.controller.storage.filestorage import ControllerFileStorage
from tierkreis.controller.executor.uv_executor import UvExecutor

root_loc = Loc()


def build_ansatz() -> Circuit:
    # TODO: This isn't a very good ansatz
    a = fresh_symbol("a")
    b = fresh_symbol("b")
    c = fresh_symbol("c")
    circ = Circuit(4)
    circ.CX(0, 1)
    circ.CX(1, 2)
    circ.CX(2, 3)
    circ.Rz(a, 3)
    circ.CX(2, 3)
    circ.CX(1, 2)
    circ.CX(0, 1)
    circ.Rz(b, 0)
    circ.CX(0, 1)
    circ.CX(1, 2)
    circ.CX(2, 3)
    circ.Rz(c, 3)
    circ.CX(2, 3)
    circ.CX(1, 2)
    circ.CX(0, 1)
    return circ


def _compute_terms() -> GraphData:
    g = GraphData()
    accum = g.add(Input("accum"))("accum")
    value = g.add(Input("value"))("value")

    untupled = g.add(Func("builtins.untuple", {"value": value}))
    res_0 = untupled("a")
    res_1 = untupled("b")

    # TODO: these aren't integers, this only works
    # because these methods are untyped
    prod = g.add(
        Func(
            "builtins.itimes",
            {"a": res_0, "b": res_1},
        )
    )("value")

    sum = g.add(
        Func(
            "builtins.iadd",
            {"a": accum, "b": prod},
        )
    )("value")

    g.add(Output({"value": sum}))

    return g


def _fold_graph_outer() -> GraphData:
    g = GraphData()

    func = g.add(Input("func"))("func")
    accum = g.add(Input("accum"))("accum")
    values = g.add(Input("values"))("values")

    zero = g.add(Const(0))("value")
    values_len = g.add(Func("builtins.len", {"l": values}))("value")
    # True if there is more than one value in the list.
    non_empty = g.add(Func("builtins.igt", {"a": values_len, "b": zero}))("value")

    # Will only succeed if values is non-empty.
    headed = g.add(Func("builtins.head", {"l": values}))

    # Apply the function if we were able to pop off a value.
    applied_next = g.add(
        Eval(
            func,
            {"accum": accum, "value": headed("head")},
        )
    )("value")

    next_accum = g.add(IfElse(non_empty, applied_next, accum))("value")
    next_values = g.add(IfElse(non_empty, headed("rest"), values))("value")
    g.add(
        Output(
            {"accum": next_accum, "values": next_values, "should_continue": non_empty}
        )
    )
    return g


# fold : {func: (b -> a -> b)} -> {initial: b} -> {values: list[a]} -> {value: b}
def _fold_graph() -> GraphData:
    g = GraphData()

    func = g.add(Input("func"))("func")
    initial = g.add(Input("initial"))("initial")
    values = g.add(Input("values"))("values")

    helper = g.add(Const(_fold_graph_outer()))("value")
    # TODO: include the computation inside the fold
    loop = g.add(
        Loop(
            helper,
            {"func": func, "accum": initial, "values": values},
            "should_continue",
        )
    )

    g.add(Output({"value": loop("accum")}))

    return g


def _subgraph() -> GraphData:
    g = GraphData()

    circuit = g.add(Input("circuit"))("circuit")
    pauli_string = g.add(Input("pauli_string"))("pauli_string")
    n_shots = g.add(Input("n_shots"))("n_shots")

    measurement_circuit = g.add(
        Func(
            "pytket_worker.append_pauli_measurement",
            {"circuit": circuit, "pauli_string": pauli_string},
        )
    )("circuit")

    # TODO: A better compilation pass
    compiled_circuit = g.add(
        Func("pytket_worker.optimise_phase_gadgets", {"circuit": measurement_circuit})
    )("circuit")

    backend_result = g.add(
        Func(
            "aer_worker.submit_single",
            {"circuit": compiled_circuit, "n_shots": n_shots},
        )
    )("backend_result")

    expectation = g.add(
        Func(
            "pytket_worker.expectation",
            {"backend_result": backend_result},
        )
    )("expectation")

    g.add(Output({"expectation": expectation}))
    return g


def symbolic_execution() -> GraphData:
    """A graph that substitutes 3 parameters into a circuit and gets an expectation value."""
    g = GraphData()
    a = g.add(Input("a"))("a")
    b = g.add(Input("b"))("b")
    c = g.add(Input("c"))("c")
    hamiltonian = g.add(Input("ham"))("ham")
    ansatz = g.add(Input("ansatz"))("ansatz")
    n_shots = g.add(Const(100))("value")

    substituted_circuit = g.add(
        Func(
            "substitution_worker.substitute",
            {"a": a, "b": b, "c": c, "circuit": ansatz},
        )
    )("circuit")

    unzipped = g.add(Func("builtins.unzip", {"value": hamiltonian}))
    pauli_strings_list = unzipped("a")
    parameters_list = unzipped("b")

    pauli_expectation = g.add(Const(_subgraph()))("value")
    unfolded_pauli_strings = g.add(
        Func("builtins.unfold_values", {"value": pauli_strings_list})
    )
    m = g.add(
        Map(
            pauli_expectation,
            unfolded_pauli_strings("*")[0],
            "pauli_string",
            "expectation",
            {"circuit": substituted_circuit, "n_shots": n_shots},
        )
    )
    folded_expectations = g.add(Func("builtins.fold_values", {"values_glob": m("*")}))(
        "value"
    )
    zipped = g.add(
        Func("builtins.zip", {"a": folded_expectations, "b": parameters_list})
    )("value")

    fold_graph = g.add(Const(_fold_graph()))("value")
    compute_graph = g.add(Const(_compute_terms()))("value")
    initial = g.add(Const(0))("value")
    # (\(x,y) \z --> x*y+z) and 0
    # TODO: This needs a better name
    computed = g.add(
        Eval(fold_graph, {"func": compute_graph, "initial": initial, "values": zipped})
    )("value")

    g.add(Output({"computed": computed}))
    return g


def main() -> None:
    """Configure our workflow execution and run it to completion."""
    ansatz = build_ansatz()

    # Assign a fixed uuid for our workflow.
    workflow_id = UUID(int=102)
    storage = ControllerFileStorage(workflow_id, name="hamiltonian", do_cleanup=True)

    # Look for workers in the same directory as this file.
    registry_path = Path(__file__).parent
    # Look for workers in the `example_workers` directory.
    registry_path = Path(__file__).parent / "example_workers"
    custom_executor = UvExecutor(
        registry_path=registry_path, logs_path=storage.logs_path
    )
    common_registry_path = Path(__file__).parent.parent / "tierkreis_workers"
    common_executor = UvExecutor(
        registry_path=common_registry_path, logs_path=storage.logs_path
    )
    multi_executor = MultipleExecutor(
        common_executor,
        executors={"custom": custom_executor},
        assignments={"substitution_worker": "custom"},
    )
    print("Starting workflow at location:", storage.logs_path)

    qubits = [Qubit(0), Qubit(1), Qubit(2), Qubit(3)]
    hamiltonian = [
        (QubitPauliString(qubits, [Pauli.X, Pauli.Y, Pauli.X, Pauli.I]).to_list(), 0.1),
        (QubitPauliString(qubits, [Pauli.Y, Pauli.Z, Pauli.X, Pauli.Z]).to_list(), 0.5),
        (QubitPauliString(qubits, [Pauli.X, Pauli.Y, Pauli.Z, Pauli.I]).to_list(), 0.3),
        (QubitPauliString(qubits, [Pauli.Z, Pauli.Y, Pauli.X, Pauli.Y]).to_list(), 0.6),
    ]
    run_graph(
        storage,
        multi_executor,
        symbolic_execution(),
        {
            "ansatz": json.dumps(ansatz.to_dict()).encode(),
            "a": json.dumps(0.2).encode(),
            "b": json.dumps(0.55).encode(),
            "c": json.dumps(0.75).encode(),
            "ham": json.dumps(hamiltonian).encode(),
        },
        polling_interval_seconds=0.1,
    )
    output = json.loads(storage.read_output(root_loc, "computed"))
    print(output)


if __name__ == "__main__":
    main()
