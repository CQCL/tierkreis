import logging
from sys import argv
from typing import NamedTuple


from default_pass import default_compilation_pass
from tierkreis import Worker
from pytket.backends.backendresult import BackendResult
from pytket._tket.circuit import Circuit
from pytket.transform import Transform
from pytket.pauli import QubitPauliString
from pytket.passes import BasePass
from pytket.utils.expectations import expectation_from_counts
from pytket.utils.measurements import append_pauli_measurement

logger = logging.getLogger(__name__)

worker = Worker("pytket_worker")


class CircuitsResult(NamedTuple):
    circuits: list[Circuit]


@worker.function()
def add_measure_all(circuit: Circuit) -> Circuit:
    circuit.measure_all()
    return circuit


@worker.function(name="append_pauli_measurement")
def append_pauli_measurement_impl(
    circuit: Circuit, pauli_string: QubitPauliString
) -> Circuit:
    append_pauli_measurement(pauli_string, circuit)
    return circuit


@worker.function()
def optimise_phase_gadgets(circuit: Circuit) -> Circuit:
    Transform.OptimisePhaseGadgets().apply(circuit)
    return circuit


@worker.function()
def apply_pass(circuit: Circuit, compiler_pass: BasePass) -> Circuit:
    compiler_pass.apply(circuit)
    return circuit


@worker.function()
def compile_circuit_quantinuum(circuit: Circuit) -> Circuit:
    p = default_compilation_pass()
    p.apply(circuit)
    return circuit


@worker.function()
def compile_circuits_quantinuum(circuits: list[Circuit]) -> list[Circuit]:
    p = default_compilation_pass()
    for pytket_circuit in circuits:
        p.apply(pytket_circuit)
    return circuits


@worker.function()
def expectation(backend_result: BackendResult) -> float:
    expectation = expectation_from_counts(backend_result.get_counts())
    return expectation


if __name__ == "__main__":
    worker.app(argv)
