from sys import argv

from tierkreis import Worker
from pytket._tket.circuit import Circuit
from pytket.backends.backendresult import BackendResult
from pytket.extensions.qulacs.backends.qulacs_backend import QulacsBackend

worker = Worker("qulacs_worker")
backend = QulacsBackend()


@worker.task()
def get_compiled_circuit(circuit: Circuit, optimisation_level: int | None) -> Circuit:
    return backend.get_compiled_circuit(circuit, optimisation_level or 2)


@worker.task()
def run_circuit(circuit: Circuit, n_shots: int) -> BackendResult:
    return backend.run_circuit(circuit, n_shots)


@worker.task()
def run_circuits(circuits: list[Circuit], n_shots: list[int]) -> list[BackendResult]:
    return backend.run_circuits(circuits, n_shots)


if __name__ == "__main__":
    worker.app(argv)
