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
from pytket.transform import Transform
from pytket.utils.expectations import expectation_from_counts
from pytket.utils.measurements import append_pauli_measurement
from pytket.backends.backendinfo import BackendInfo

from qnexus import BackendConfig, IBMQConfig, QuantinuumConfig
from tierkreis.exceptions import TierkreisError

from tierkreis import Worker

worker = Worker("pytket_worker")


@worker.task()
def get_backend_info(config: BackendConfig) -> BackendInfo:
    """Retrieves a BackendInfo object for a given configuration.

    Depending on the backend, this requires authorization.
    The BackendInfo can be reused for different compilation tasks without refetching.

    :param config: The user provide configuration of the backend to use.
    :type config: BackendConfig
    :raises TierkreisError: If the pytket-quantinuum and pytket-qiskit extensions are not available.
    :raises TierkreisError: If no available backend matches the provided configuration.
    :raises NotImplementedError: If a backend is requested that's neither IBMQ nor Quantinuum.
    :return: The BackendInfo if the device was available
    :rtype: BackendInfo
    """
    try:
        from pytket.extensions.qiskit.backends.ibm import IBMQBackend
        from pytket.extensions.quantinuum.backends.quantinuum import QuantinuumBackend
    except ModuleNotFoundError as e:
        raise TierkreisError("Pytket worker could not import extension backends") from e
    match config:
        case IBMQConfig():
            info = next(
                filter(
                    lambda x: x.name == config.backend_name,
                    IBMQBackend.available_devices(),
                ),
                None,
            )
            if info is None:
                raise TierkreisError(
                    f"Device {config.backend_name} is not in the list of available IBMQ devices"
                )
            return info
        case QuantinuumConfig():
            info = next(
                filter(
                    lambda x: x.name == config.device_name,
                    QuantinuumBackend.available_devices(),
                ),
                None,
            )
            if info is None:
                raise TierkreisError(
                    f"Device {config.device_name} is not in the list of available Quantinuum devices"
                )
            return info
        case _:
            raise NotImplementedError()


@worker.task()
def compile_using_info(
    circuit: Circuit,
    backend_info: BackendInfo,
    config: BackendConfig,
    optimisation_level: int = 2,
    timeout: int = 300,
) -> Circuit:
    """Generic task compile a circuit for a backend info according to the backend config.

    Compiles for a previously acquired backend information using the same config.

    :param circuit: The original circuit.
    :type circuit: Circuit
    :param backend_info: The backend info to get the optimization pass from.
    :type backend_info: BackendInfo
    :param config: The backend configuration provided by the user.
    :type config: BackendConfig
    :param optimisation_level: The optimization level for the compilation, defaults to 2
    :type optimisation_level: int
    :param timeout: Timeout to wait for the pass to arrive, defaults to 300
    :type timeout: int
    :raises TierkreisError: If the pytket-quantinuum and pytket-qiskit extensions are not available.
    :raises NotImplementedError: If a backend is requested that's neither IBMQ nor Quantinuum.
    :return: The compiled circuit.
    :rtype: Circuit
    """
    try:
        from pytket.extensions.qiskit.backends.ibm import IBMQBackend
        from pytket.extensions.quantinuum.backends.quantinuum import QuantinuumBackend
    except ModuleNotFoundError as e:
        raise TierkreisError("Pytket worker could not import extension backends") from e
    match config:
        case IBMQConfig():
            compilation_pass = IBMQBackend.pass_from_info(
                backend_info, optimisation_level, timeout
            )
        case QuantinuumConfig():
            compilation_pass = QuantinuumBackend.pass_from_info(
                backend_info, optimisation_level=optimisation_level, timeout=timeout
            )
        case _:
            raise NotImplementedError()
    compilation_pass.apply(circuit)
    return circuit


@worker.task()
def ibmq_offline_pass(
    backend_info: BackendInfo, optimisation_level: int = 2
) -> BasePass:
    """Fetches an compilation pass from a BackendInfo of a IBMQ backend.

    :param backend_info: The backend info to get the pass for.
    :type backend_info: BackendInfo
    :param optimisation_level: The optimization level for the compilation, defaults to 2
    :type optimisation_level: int, optional
    :raises TierkreisError: If the pytket-qiskit extension is not installed.
    :return: The default compilation pass given the backend.
    :rtype: BasePass
    """
    try:
        from pytket.extensions.qiskit.backends.ibm import IBMQBackend

        return IBMQBackend.pass_from_info(backend_info, optimisation_level)
    except ModuleNotFoundError as e:
        raise TierkreisError(
            "Pytket worker could not instantiate IBMQBackend. Make sure pytket-qiskit is installed"
        ) from e


@worker.task()
def quantinuum_offline_pass(
    backend_info: BackendInfo, optimisation_level: int = 2
) -> BasePass:
    """Fetches an compilation pass from a BackendInfo of a Quantinuum backend.

    :param backend_info: The backend info to get the pass for.
    :type backend_info: BackendInfo
    :param optimisation_level: The optimization level for the compilation, defaults to 2
    :type optimisation_level: int, optional
    :raises TierkreisError: If the pytket-quantinuum extension is not installed.
    :return: The default compilation pass given the backend.
    :rtype: BasePass
    """
    try:
        from pytket.extensions.quantinuum.backends.quantinuum import QuantinuumBackend

        return QuantinuumBackend.pass_from_info(
            backend_info, optimisation_level=optimisation_level
        )
    except ModuleNotFoundError as e:
        raise TierkreisError(
            "Pytket worker could not instantiate QuantinuumBackend. Make sure pytket-quantinuum is installed"
        ) from e


@worker.task()
def add_measure_all(circuit: Circuit) -> Circuit:
    """Appends final measurements to all qubits.

    :param circuit: The original circuit.
    :type circuit: Circuit
    :return: Circuit with measurement on all qubits.
    :rtype: Circuit
    """
    circuit.measure_all()
    return circuit


@worker.task()
def append_pauli_measurement_impl(
    circuit: Circuit, pauli_string: QubitPauliString
) -> Circuit:
    """Appends pauli measurements according to the pauli string to the circuit.

    :param circuit: The original circuit.
    :type circuit: Circuit
    :param pauli_string: The Pauli String describing an observable.
    :type pauli_string: QubitPauliString
    :return: The updated circuits withe measurements attached.
    :rtype: Circuit
    """
    append_pauli_measurement(pauli_string, circuit)
    return circuit


@worker.task()
def optimise_phase_gadgets(circuit: Circuit) -> Circuit:
    """Applies an optimization pass to the circuit.

    The optimization pass is based on identifying phase gadget structures
    in subcircuits of the circuit.

    :param circuit: The original circuit.
    :type circuit: Circuit
    :return: The optimized circuit.
    :rtype: Circuit
    """
    Transform.OptimisePhaseGadgets().apply(circuit)
    return circuit


@worker.task()
def apply_pass(circuit: Circuit, compiler_pass: BasePass) -> Circuit:
    """Applies an arbitrary optimization pass to the circuit

    :param circuit: The original circuit.
    :type circuit: Circuit
    :param compiler_pass: The pass to apply to the circuit.
    :type compiler_pass: BasePass
    :return: The optimized circuit.
    :rtype: Circuit
    """
    compiler_pass.apply(circuit)
    return circuit


@worker.task()
def compile(
    circuit: Circuit | str | bytes,
    input_format: str = "TKET",
    optimisation_level: int = 2,
    gate_set: list[str] | None = None,
    coupling_map: list[tuple[int, int]] | None = None,
    output_format: str = "TKET",
    optimisation_pass: BasePass | None = None,
) -> Circuit | str | bytes:
    """Generic compilation function.

    When no optimization pass is provided a generic one will be applied.
    The passes are indicated for which optimizatino level they apply:
    - DecomposeBoxes, [0,1,2,3]
    - First round
        - AutoRebase, [0]
        - SynthesiseTket, AutoSquash, [1]
        - FullPeepholeOptimise, [2]
        - RemoveBarries, AutoRebase, GreedyPauliSimp, [3]
    - Mapping, [0,1,2,3] if not all-to-all
        - AutoRebase, FullMappingPass(Graph, LexiLabel, LexiRouting)
    - Second round
        - SynthesiseTket, [1,3]
        - KAKDecomposition, CliffordSimpm, SynthesiseTket, [2]
    - AutoRebase, AutoSquash, RemoveRedundancies, [0,1,2,3]

    The input format is checked against the circuit; if they don't match an error will be raised.
    The matching is as follows:
    - Circuit: TKET
    - str: QASM2
    - bytes: QIR
    When no coupling map is provided an all-to-all connectivity is assumed, no mapping will take place.
    The qubit number is inferred from the number of qubits in the circuit.
    The coupling map is expected as a tuple of integers, from which the maximum number of qubits will be inferred.
    When no gate_set is provide a minimal gate set of {Rx, Rz, CX} is used.
    Gates in the gate set are matched to the pytket OpTypes.

    :param circuit: The circuit to optimize.
    :type circuit: Circuit | str | bytes
    :param input_format: The desired input format, defaults to "TKET"
    :type input_format: str in ["TKET", "QASM2", "QIR"], optional
    :param optimisation_level: Level of optimization to perform, defaults to 2
    :type optimisation_level: int, optional
    :param gate_set: A set of OpTypes as strings for hardware restrictions, defaults to None
    :type gate_set: list[str] | None, optional
    :param coupling_map: Connectivity constraint, fidelities are not regarded , defaults to None
    :type coupling_map: list[tuple[int, int]] | None, optional
    :param output_format: The desired output formt, defaults to "TKET"
    :type output_format: str in ["TKET", "QASM2", "QIR"], optional
    :param optimisation_pass: A custom optimization pass to be applied, defaults to None
    :type optimisation_pass: BasePass | None, optional
    :return: The circuit in the desired output format.
    :rtype: Circuit | str | bytes
    """
    # Enums are currently not available, so we use strings and parse

    if gate_set is None:
        gate_set_op = MINIMAL_GATE_SET
    else:
        op_types = {op_type.name: op_type for op_type in OpType}
        gate_set_op = set(op_types[gate] for gate in gate_set)

    return compile_circuit(
        circuit,
        CircuitFormat[input_format],
        OptimizationLevel(optimisation_level),
        gate_set_op,
        coupling_map,
        CircuitFormat[output_format],
        optimisation_pass,
    )


@worker.task()
def compile_circuit_quantinuum(circuit: Circuit) -> Circuit:
    """Applies a predefined optimization pass for Quantinuum devices.

    The optimization pass corresponds to a level=3 optimization.

    :param circuit: The original circuit.
    :type circuit: Circuit
    :return: The optimized circuit.
    :rtype: Circuit
    """
    p = default_compilation_pass()
    p.apply(circuit)
    return circuit


@worker.task()
def compile_circuits_quantinuum(circuits: list[Circuit]) -> list[Circuit]:
    """Applies a predefined optimization pass for Quantinuum devices.

    :param circuits: A list of circuits to be optimized.
    :type circuits: list[Circuit]
    :return: The optimized circuits.
    :rtype: list[Circuit]
    """
    p = default_compilation_pass()
    for pytket_circuit in circuits:
        p.apply(pytket_circuit)
    return circuits


@worker.task()
def compile_tket_circuit_ibm(
    circuit: Circuit, backend_name: str, optimisation_level: int = 2
) -> Circuit:
    """Applies pytkets default compilation pass for IBMQ devices.

    The device is constructed by name, this function needs credentials.

    :param circuit: The original circuit.
    :type circuit: Circuit
    :param backend_name: The name of the IBMQ backend.
    :type backend_name: str
    :param optimisation_level: Level of optimization in [0,1,2,3], defaults to 2
    :type optimisation_level: int, optional
    :return: The optimized circuit.
    :rtype: Circuit
    """
    p = default_compilation_pass_ibm(backend_name, optimisation_level)
    p.apply(circuit)
    return circuit


@worker.task()
def compile_tket_circuits_ibm(
    circuits: list[Circuit], backend_name: str, optimisation_level: int = 2
) -> list[Circuit]:
    """Applies pytkets default compilation pass for IBMQ devices.

    The device is constructed by name, this function needs credentials.

    :param circuits: A list of circuits to be optimized.
    :type circuits: list[Circuit]
    :param backend_name: The name of the IBMQ backend.
    :type backend_name: str
    :param optimisation_level: Level of optimization in [0,1,2,3], defaults to 2
    :type optimisation_level: int, optional
    :return: The optimized circuits.
    :rtype: list[Circuit]
    """
    p = default_compilation_pass_ibm(backend_name, optimisation_level)
    for pytket_circuit in circuits:
        p.apply(pytket_circuit)
    return circuits


@worker.task()
def compile_tket_circuit_quantinuum(
    circuit: Circuit, backend_name: str, optimisation_level: int = 2
) -> Circuit:
    """Applies pytkets default compilation pass for Quantinuum devices.

    The device is constructed by name, this function needs credentials.

    :param circuit: The original circuit.
    :type circuit: Circuit
    :param backend_name: The name of the Quantinuum backend.
    :type backend_name: str
    :param optimisation_level: Level of optimization in [0,1,2,3], defaults to 2
    :type optimisation_level: int, optional
    :return: The optimized circuit.
    :rtype: Circuit
    """
    p = default_compilation_pass_quantinuum(backend_name, optimisation_level)
    p.apply(circuit)
    return circuit


@worker.task()
def compile_tket_circuits_quantinuum(
    circuits: list[Circuit], backend_name: str, optimisation_level: int = 2
) -> list[Circuit]:
    """Applies pytkets default compilation pass for Quantinuum devices.

    The device is constructed by name, this function needs credentials.

    :param circuits: A list of circuits to be optimized.
    :type circuits: list[Circuit]
    :param backend_name: The name of the Quantinuum backend.
    :type backend_name: str
    :param optimisation_level: Level of optimization in [0,1,2,3], defaults to 2
    :type optimisation_level: int, optional
    :return: The optimized circuits.
    :rtype: list[Circuit]
    """
    p = default_compilation_pass_quantinuum(backend_name, optimisation_level)
    for pytket_circuit in circuits:
        p.apply(pytket_circuit)
    return circuits


@worker.task()
def to_qasm_str(circuit: Circuit, header: str = "qelib1") -> str:
    """Transforms a pytket circuit into a QASM2 string.

    :param circuit: The original circuit.
    :type circuit: Circuit
    :param header: The QASM2 header lib to use.
    :type header: str
    :return: The circuit in QASM2 representation.
    :rtype: str
    """
    return circuit_to_qasm_str(circuit, header)


@worker.task()
def from_gasm_str(qasm: str) -> Circuit:
    """Generates a pytket circuit from a QASM2 string.

    :param qasm: The circuit in QASM2 representation.
    :type qasm: str
    :return: The corresponding pytket circuit.
    :rtype: Circuit
    """
    return circuit_from_qasm_str(qasm)


@worker.task()
def to_qir_bytes(circuit: Circuit) -> bytes:
    """Generate qir bytecode from the pytket circuit.

    :param circuit: The original circuit.
    :type circuit: Circuit
    :return: The circuit as QIR bytecode.
    :rtype: bytes
    """
    try:
        from pytket.qir.conversion.api import pytket_to_qir
    except ModuleNotFoundError:
        raise TierkreisError("Could not resolve pytket.qir")
    ret = pytket_to_qir(circuit)
    if not isinstance(ret, bytes):
        raise TierkreisError("Error when converting Circuit to QIR.")
    return ret


@worker.task()
def from_qir_bytes(qir: bytes) -> Circuit:
    """Converts qir bytecode into a pytket circuit.

    :param qir: The QIR bytecode.
    :type qir: bytes
    :return: The corresponding pytket circuit.
    :rtype: Circuit
    """
    try:
        from pytket_qirpass import qir_to_pytket
    except ModuleNotFoundError:
        raise TierkreisError("Could not resolve pytket_qirpass")
    return qir_to_pytket(qir)


@worker.task()
def expectation(backend_result: BackendResult) -> float:
    """Estimates the expectation value from a circuits shot counts.

    :param backend_result: Results from a pytket backend.
    :type backend_result: BackendResult
    :return: The estimated expectation value.
    :rtype: float
    """
    expectation = expectation_from_counts(backend_result.get_counts())
    return expectation


@worker.task()
def n_qubits(circuit: Circuit) -> int:
    """Wrapper for pytket.Circuit.n_qubits.

    :param circuit: The pytket circuit.
    :type circuit: Circuit
    :return: The number of qubits in that circuit.
    :rtype: int
    """
    return circuit.n_qubits


def main():
    worker.app(argv)


if __name__ == "__main__":
    main()
