from sys import argv

from pytket._tket.circuit import Circuit
from pytket.backends.backendinfo import BackendInfo
from pytket.extensions.quantinuum.backends.quantinuum import QuantinuumBackend
from pytket.passes import BasePass

from tierkreis import Worker
from tierkreis.exceptions import TierkreisError

from default_pass_quantinuum import default_compilation_pass

worker = Worker("quantinuum_worker")


@worker.task()
def get_backend_info(device_name: str) -> BackendInfo:
    info = next(
        filter(
            lambda x: x.name == device_name,
            QuantinuumBackend.available_devices(),
        ),
        None,
    )
    if info is None:
        raise TierkreisError(
            f"Device {device_name} is not in the list of available Quantinuum devices"
        )
    return info


@worker.task()
def backend_pass_from_info(
    backend_info: BackendInfo, optimisation_level: int = 2
) -> BasePass:
    return QuantinuumBackend.pass_from_info(
        backend_info, optimisation_level=optimisation_level
    )


@worker.task()
def backend_default_compilation_pass(
    device_name: str, optimisation_level: int = 2
) -> BasePass:
    backend = QuantinuumBackend(device_name)
    return backend.default_compilation_pass(optimisation_level)


@worker.task()
def fixed_pass() -> BasePass:
    return default_compilation_pass()


@worker.task()
def compile(
    circuit: Circuit,
    device_name: str,
    optimisation_level: int = 2,
) -> Circuit:
    backend = QuantinuumBackend(device_name)
    compilation_pass = backend.default_compilation_pass(optimisation_level)
    compilation_pass.apply(circuit)
    return circuit


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


def main():
    worker.app(argv)


if __name__ == "__main__":
    main()
