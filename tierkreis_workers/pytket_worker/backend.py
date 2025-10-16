"""Wrappers around pytket backend methods.

For now only support simulators as they are easy to instantiate.
If we want to support more backends we should try to reuse code from
https://github.com/quantinuum-dev/mushroom/tree/main/libraries/nexus-pytket
"""

from qnexus import BackendConfig
from pytket._tket.circuit import Circuit
from pytket.backends.backend import Backend
from pytket.backends.backendresult import BackendResult
from quantinuum_schemas.models.backend_config import AerConfig, QulacsConfig


def get_backend(config: BackendConfig) -> Backend:
    match config:
        case AerConfig():
            from pytket.extensions.qiskit.backends.aer import AerBackend

            return AerBackend(
                simulation_method=config.simulation_method, n_qubits=config.n_qubits
            )
        case QulacsConfig():
            from pytket.extensions.qulacs.backends.qulacs_backend import QulacsBackend

            return QulacsBackend(config.result_type)
        case _:
            raise NotImplementedError(f"Config {config} is not supported.")


def get_compiled_circuit(
    circuit: Circuit, optimisation_level: int | None, config: BackendConfig
) -> Circuit:
    backend = get_backend(config)
    return backend.get_compiled_circuit(
        circuit=circuit, optimisation_level=optimisation_level or 2
    )


def run_circuit(
    circuit: Circuit,
    n_shots: int,
    config: BackendConfig,
) -> BackendResult:
    backend = get_backend(config)
    return backend.run_circuit(circuit, n_shots)


def run_circuits(
    circuits: list[Circuit],
    n_shots: list[int],
    config: BackendConfig,
) -> list[BackendResult]:
    backend = get_backend(config)
    return backend.run_circuits(circuits, n_shots)
