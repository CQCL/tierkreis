# /// script
# requires-python = ">=3.12"
# dependencies = ["tierkreis", "pytket"]
#
# [tool.uv.sources]
# tierkreis = { path = "../tierkreis", editable = true }
# ///
import json
from pathlib import Path
from typing import NamedTuple, Literal
from uuid import UUID

from pytket._tket.unit_id import Qubit
from pytket.pauli import Pauli, QubitPauliString
from pytket._tket.circuit import Circuit, fresh_symbol
from tierkreis.builder import GraphBuilder
from tierkreis.controller import run_graph
from tierkreis.controller.data.location import Loc
from tierkreis.controller.data.models import TKR
from tierkreis.controller.executor.multiple import MultipleExecutor
from tierkreis.controller.storage.filestorage import ControllerFileStorage
from tierkreis.controller.executor.uv_executor import UvExecutor

from tierkreis.builtins.stubs import untuple, itimes, iadd, unzip, zip_impl
from tierkreis.graphs.fold import FoldGraphInputs, fold_graph
from example_workers.pytket_worker.stubs import (
    append_pauli_measurement_impl,
    optimise_phase_gadgets,
    expectation,
)

from example_workers.aer_worker.stubs import submit_single
from example_workers.substitution_worker.stubs import substitute

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


class ComputeTermsInputs(NamedTuple):
    accum: TKR[int]
    value: TKR[tuple]


def _compute_terms():
    g = GraphBuilder(ComputeTermsInputs, TKR[int])

    untupled = g.task(untuple(g.inputs.value))
    res_0 = untupled.a
    res_1 = untupled.b

    # TODO: these aren't integers, this only works
    # because these methods are untyped
    prod = g.task(itimes(res_0, res_1))
    sum = g.task(iadd(g.inputs.accum, prod))

    g.outputs(sum)
    return g


class SubgraphInputs(NamedTuple):
    circuit: TKR[Literal["pytket._tket.circuit.Circuit"]]
    pauli_string: TKR[Literal["pytket._tket.pauli.QubitPauliString"]]
    n_shots: TKR[int]


def _subgraph():
    g = GraphBuilder(SubgraphInputs, TKR[float])

    circuit = g.inputs.circuit
    pauli_string = g.inputs.pauli_string
    n_shots = g.inputs.n_shots

    measurement_circuit = g.task(append_pauli_measurement_impl(circuit, pauli_string))

    # TODO: A better compilation pass
    compiled_circuit = g.task(optimise_phase_gadgets(measurement_circuit))

    backend_result = g.task(submit_single(compiled_circuit, n_shots))
    av = g.task(expectation(backend_result))
    g.outputs(av)
    return g


class SymbolicExecutionInputs(NamedTuple):
    a: TKR[float]
    b: TKR[float]
    c: TKR[float]
    ham: TKR[list[tuple[Literal["pytket._tket.pauli.QubitPauliString"], float]]]
    ansatz: TKR


def symbolic_execution():
    """A graph that substitutes 3 parameters into a circuit and gets an expectation value."""
    g = GraphBuilder(SymbolicExecutionInputs, TKR[float])
    a = g.inputs.a
    b = g.inputs.b
    c = g.inputs.c
    hamiltonian = g.inputs.ham
    ansatz = g.inputs.ansatz

    substituted_circuit = g.task(substitute(ansatz, a, b, c))
    unzipped = g.task(unzip(hamiltonian))
    pauli_strings_list: TKR[list[Literal["pytket._tket.pauli.QubitPauliString"]]] = (
        unzipped.a  # type: ignore
    )
    parameters_list = unzipped.b

    aes = g.map(
        pauli_strings_list,
        lambda x: SubgraphInputs(substituted_circuit, x, g.const(100)),
    )
    m = g.map(aes, _subgraph())
    zipped = g.task(zip_impl(m, parameters_list))
    compute_graph = g.const(_compute_terms().get_data())
    # (\(x,y) \z --> x*y+z) and 0
    # TODO: This needs a better name
    computed = g.eval(
        fold_graph(),
        FoldGraphInputs[float, float](compute_graph, g.const(0.0), zipped),
    )
    g.outputs(computed)
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
        symbolic_execution().get_data(),
        {
            "ansatz": json.dumps(ansatz.to_dict()).encode(),
            "a": json.dumps(0.2).encode(),
            "b": json.dumps(0.55).encode(),
            "c": json.dumps(0.75).encode(),
            "ham": json.dumps(hamiltonian).encode(),
        },
        polling_interval_seconds=0.1,
    )
    output = json.loads(storage.read_output(root_loc, "value"))
    print(output)


if __name__ == "__main__":
    main()
