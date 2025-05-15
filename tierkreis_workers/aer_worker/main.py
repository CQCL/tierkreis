import logging
from sys import argv
from pathlib import Path

from pydantic import BaseModel
from tierkreis import Worker
from pytket._tket.circuit import Circuit
from pytket.extensions.qiskit.backends.aer import AerBackend

logger = logging.getLogger(__name__)

worker = Worker("aer-worker")


class BackendResults(BaseModel):
    backend_results: list[dict]


@worker.function()
def submit(circuits: list[dict], n_shots: int) -> BackendResults:
    pytket_circuits = [Circuit.from_dict(circuit) for circuit in circuits]
    backend = AerBackend()
    backend_results = backend.run_circuits(pytket_circuits, n_shots=n_shots)
    return BackendResults(
        backend_results=[backend_result.to_dict() for backend_result in backend_results]
    )


class BackendResult(BaseModel):
    backend_result: dict


@worker.function()
def submit_single(circuit: dict, n_shots: int) -> BackendResult:
    pytket_circuit = Circuit.from_dict(circuit)
    backend = AerBackend()
    backend_result = backend.run_circuit(pytket_circuit, n_shots=n_shots)
    return BackendResult(backend_result=backend_result.to_dict())


def main() -> None:
    node_definition_path = argv[1]
    logger.info(node_definition_path)
    worker.run(Path(node_definition_path))


if __name__ == "__main__":
    main()
