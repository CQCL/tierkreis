import logging
from sys import argv

from tierkreis import Worker
from pytket._tket.circuit import Circuit
from pytket.backends.backendresult import BackendResult
from pytket.extensions.qiskit.backends.aer import AerBackend

logger = logging.getLogger(__name__)

worker = Worker("aer_worker")


@worker.function()
def submit(circuits: list[Circuit], n_shots: int) -> list[BackendResult]:
    return AerBackend().run_circuits(circuits, n_shots=n_shots)


@worker.function()
def submit_single(circuit: Circuit, n_shots: int) -> BackendResult:
    return AerBackend().run_circuit(circuit, n_shots=n_shots)


if __name__ == "__main__":
    worker.app(argv)
