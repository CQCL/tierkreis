import logging
from sys import argv

from tierkreis import Worker
from pytket._tket.circuit import Circuit
from pytket.backends.backendresult import BackendResult
from pytket.extensions.qiskit.qiskit_convert import tk_to_qiskit
from pytket.extensions.qiskit.backends.aer import AerBackend
from qiskit import qasm3
from quantinuum_schemas.models.backend_config import AerConfig

logger = logging.getLogger(__name__)
worker = Worker("aer_worker")


def get_backend(config: AerConfig) -> AerBackend:
    return AerBackend(
        simulation_method=config.simulation_method, n_qubits=config.n_qubits
    )


@worker.task()
def get_compiled_circuit(
    circuit: Circuit,
    config: AerConfig,
    optimisation_level: int = 2,
    timeout: int = 300,
) -> Circuit:
    backend = get_backend(config)
    return backend.get_compiled_circuit(circuit, optimisation_level, timeout)


@worker.task()
def run_circuit(
    circuit: Circuit,
    n_shots: int,
    config: AerConfig,
) -> BackendResult:
    backend = get_backend(config)
    return backend.run_circuit(circuit, n_shots)


@worker.task()
def run_circuits(
    circuits: list[Circuit],
    n_shots: list[int],
    config: AerConfig,
) -> list[BackendResult]:
    backend = get_backend(config)
    return backend.run_circuits(circuits, n_shots)


@worker.task()
def to_qasm3_str(circuit: Circuit) -> str:
    """Transforms a pytket circuit to a QASM3 string.

    Uses qiskits qasm3 module tket circuit -> qiskit circuit -> QASM3.

    :param circuit: The original pytket circuit.
    :type circuit: Circuit
    :return: The circuit in QASM3.
    :rtype: str
    """
    return qasm3.dumps(tk_to_qiskit(circuit))


# Deprecated tasks


@worker.task()
def submit(circuits: list[Circuit], n_shots: int) -> list[BackendResult]:
    """Runs multiple circuits for n_shots on a simulated backend.

    :param circuits:  The circuits to simulate.
    :type circuits: list[Circuit]
    :param n_shots: Number of shots.
    :type n_shots: int
    :return: The aggregated results of the simulation for each circuit
    :rtype: list[BackendResult]
    """
    return AerBackend().run_circuits(circuits, n_shots=n_shots)


@worker.task()
def submit_single(circuit: Circuit, n_shots: int) -> BackendResult:
    """Runs a single circuit for n_shots on a simulated backend.

    :param circuit: The circuit to simulate.
    :type circuit: Circuit
    :param n_shots: Number of shots.
    :type n_shots: int
    :return: The aggregated results of the simulation.
    :rtype: BackendResult
    """
    return AerBackend().run_circuit(circuit, n_shots=n_shots)


def main():
    worker.app(argv)


if __name__ == "__main__":
    main()
