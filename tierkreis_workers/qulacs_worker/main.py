from sys import argv
from typing import Any, Optional

from tierkreis import Worker
from pytket._tket.circuit import Circuit
from pytket.backends.backend import Backend
from pytket.backends.backendresult import BackendResult
from pytket.extensions.qulacs.backends.qulacs_backend import QulacsBackend

worker = Worker("qulacs_worker")


def get_backend(result_type: str = "state_vector", gpu_sim: bool = False) -> Backend:
    if gpu_sim:
        from pytket.extensions.qulacs.backends.qulacs_backend import QulacsGPUBackend

        return QulacsGPUBackend()
    else:
        return QulacsBackend(result_type)


@worker.task()
def get_compiled_circuit(
    circuit: Circuit,
    optimisation_level: int = 2,
    result_type: str = "state_vector",
    gpu_sim: bool = False,
) -> Circuit:
    backend = get_backend(result_type, gpu_sim)
    return backend.get_compiled_circuit(circuit, optimisation_level)


@worker.task()
def run_circuit(
    circuit: Circuit,
    n_shots: int,
    result_type: str = "state_vector",
    gpu_sim: bool = False,
    seed: Optional[int] = None,
) -> BackendResult:
    backend = get_backend(result_type, gpu_sim)
    config: dict[str, Any] = {} if seed is None else {"seed": seed}
    return backend.run_circuit(circuit, n_shots, **config)


@worker.task()
def run_circuits(
    circuits: list[Circuit],
    n_shots: list[int],
    result_type: str = "state_vector",
    gpu_sim: bool = False,
    seed: Optional[int] = None,
) -> list[BackendResult]:
    backend = get_backend(result_type, gpu_sim)
    config: dict[str, Any] = {} if seed is None else {"seed": seed}
    return backend.run_circuits(circuits, n_shots, **config)


if __name__ == "__main__":
    worker.app(argv)
