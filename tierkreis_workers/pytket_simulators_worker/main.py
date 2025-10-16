import logging
from sys import argv

from qnexus import BackendConfig
from tierkreis import Worker
from pytket._tket.circuit import Circuit
from pytket.backends.backend import Backend
from pytket.backends.backendresult import BackendResult
from quantinuum_schemas.models.backend_config import AerConfig, QulacsConfig

logger = logging.getLogger(__name__)
worker = Worker("pytket_simulators_worker")


def get_backend(config: BackendConfig) -> Backend:
    from pytket.extensions.qiskit.backends.aer import AerBackend
    from pytket.extensions.qulacs.backends.qulacs_backend import QulacsBackend

    match config:
        case AerConfig():
            return AerBackend(
                simulation_method=config.simulation_method, n_qubits=config.n_qubits
            )
        case QulacsConfig():
            return QulacsBackend(config.result_type)
        case _:
            raise NotImplementedError(f"Config {config} is not a supported simulator.")


@worker.task()
def get_compiled_circuit(
    circuit: Circuit, optimisation_level: int | None, config: BackendConfig
) -> Circuit:
    backend = get_backend(config)
    return backend.get_compiled_circuit(
        circuit=circuit, optimisation_level=optimisation_level or 2
    )


@worker.task()
def run_circuit(
    circuit: Circuit,
    n_shots: int,
    config: BackendConfig,
) -> BackendResult:
    backend = get_backend(config)
    return backend.run_circuit(circuit, n_shots)


@worker.task()
def run_circuits(
    circuits: list[Circuit],
    n_shots: list[int],
    config: BackendConfig,
) -> list[BackendResult]:
    backend = get_backend(config)
    return backend.run_circuits(circuits, n_shots)


if __name__ == "__main__":
    worker.app(argv)
