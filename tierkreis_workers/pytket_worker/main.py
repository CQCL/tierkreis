from sys import argv

from compile_circuit import (
    MINIMAL_GATE_SET,
    CircuitFormat,
    OptimizationLevel,
    compile_circuit,
)
from default_pass import (
    default_compilation_pass,
    default_compilation_pass_ibm,
    default_compilation_pass_quantinuum,
)
from pytket._tket.circuit import Circuit
from pytket.backends.backendresult import BackendResult
from pytket.circuit import OpType
from pytket.passes import BasePass
from pytket.pauli import QubitPauliString
from pytket.qasm.qasm import circuit_from_qasm_str, circuit_to_qasm_str
from pytket.qir.conversion.api import pytket_to_qir
from pytket.transform import Transform
from pytket.utils.expectations import expectation_from_counts
from pytket.utils.measurements import append_pauli_measurement
from pytket_qirpass import qir_to_pytket
from tierkreis.exceptions import TierkreisError

from tierkreis import Worker

worker = Worker("pytket_worker")


@worker.task()
def add_measure_all(circuit: Circuit) -> Circuit:
    circuit.measure_all()
    return circuit


@worker.task(name="append_pauli_measurement")
def append_pauli_measurement_impl(
    circuit: Circuit, pauli_string: QubitPauliString
) -> Circuit:
    append_pauli_measurement(pauli_string, circuit)
    return circuit


@worker.task()
def optimise_phase_gadgets(circuit: Circuit) -> Circuit:
    Transform.OptimisePhaseGadgets().apply(circuit)
    return circuit


@worker.task()
def apply_pass(circuit: Circuit, compiler_pass: BasePass) -> Circuit:
    compiler_pass.apply(circuit)
    return circuit


@worker.task()
def compile(
    circuit: Circuit | str | bytes,
    input_format: str = "TKET",
    optimization_level: int = 2,
    gate_set: list[str] | None = None,
    coupling_map: list[tuple[int, int]] | None = None,
    output_format: str = "TKET",
    optimization_pass: BasePass | None = None,
) -> Circuit | str | bytes:
    # Enums are currently not available, so we use strings and parse

    if gate_set is None:
        gate_set_op = MINIMAL_GATE_SET
    else:
        op_types = {op_type.name: op_type for op_type in OpType}
        gate_set_op = set(op_types[gate] for gate in gate_set)

    return compile_circuit(
        circuit,
        CircuitFormat(input_format),
        OptimizationLevel(optimization_level),
        gate_set_op,
        coupling_map,
        CircuitFormat(output_format),
        optimization_pass,
    )


@worker.task()
def compile_circuit_quantinuum(circuit: Circuit) -> Circuit:
    p = default_compilation_pass()
    p.apply(circuit)
    return circuit


@worker.task()
def compile_circuits_quantinuum(circuits: list[Circuit]) -> list[Circuit]:
    p = default_compilation_pass()
    for pytket_circuit in circuits:
        p.apply(pytket_circuit)
    return circuits


@worker.task()
def compile_tket_circuit_ibm(
    circuit: Circuit, backend_name: str, optimization_level: int = 2
) -> Circuit:
    p = default_compilation_pass_ibm(backend_name, optimization_level)
    p.apply(circuit)
    return circuit


@worker.task()
def compile_tket_circuits_ibm(
    circuits: list[Circuit], backend_name: str, optimization_level: int = 2
) -> list[Circuit]:
    p = default_compilation_pass_ibm(backend_name, optimization_level)
    for pytket_circuit in circuits:
        p.apply(pytket_circuit)
    return circuits


@worker.task()
def compile_tket_circuit_quantinuum(
    circuit: Circuit, backend_name: str, optimization_level: int = 2
) -> Circuit:
    p = default_compilation_pass_quantinuum(backend_name, optimization_level)
    p.apply(circuit)
    return circuit


@worker.task()
def compile_tket_circuits_quantinuum(
    circuits: list[Circuit], backend_name: str, optimization_level: int = 2
) -> list[Circuit]:
    p = default_compilation_pass_quantinuum(backend_name, optimization_level)
    for pytket_circuit in circuits:
        p.apply(pytket_circuit)
    return circuits


@worker.task()
def to_qasm_str(circuit: Circuit) -> str:
    return circuit_to_qasm_str(circuit)


@worker.task()
def from_gasm_str(qasm: str) -> Circuit:
    return circuit_from_qasm_str(qasm)


@worker.task()
def to_qir_bytes(circuit: Circuit) -> bytes:
    ret = pytket_to_qir(circuit)
    if not isinstance(ret, bytes):
        raise TierkreisError("Error when converting Circuit to QIR.")
    return ret


@worker.task()
def from_qir_bytes(qir: bytes) -> Circuit:
    return qir_to_pytket(qir)


@worker.task()
def expectation(backend_result: BackendResult) -> float:
    expectation = expectation_from_counts(backend_result.get_counts())
    return expectation


if __name__ == "__main__":
    worker.app(argv)
