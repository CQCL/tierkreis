import logging
from sys import argv

from tierkreis import Worker
from pytket._tket.circuit import Circuit
from pytket.backends.backendresult import BackendResult
from pytket.extensions.qiskit.backends.aer import AerBackend

logger = logging.getLogger(__name__)

worker = Worker("aer_worker")


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
