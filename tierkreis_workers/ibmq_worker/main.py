from sys import argv
from typing import Sequence

from pytket._tket.circuit import Circuit
from pytket.architecture import Architecture
from pytket.backends.backendinfo import BackendInfo
from pytket.extensions.qiskit.backends.ibm import IBMQBackend
from pytket.passes import BasePass


from tierkreis import Worker
from tierkreis.exceptions import TierkreisError

from default_pass import default_compilation_pass, IBMQ_GATE_SET

worker = Worker("ibmq_worker")


@worker.task()
def get_backend_info(device_name: str) -> BackendInfo:
    info = next(
        filter(
            lambda x: x.name == device_name,
            IBMQBackend.available_devices(),
        ),
        None,
    )
    if info is None:
        raise TierkreisError(
            f"Device {device_name} is not in the list of available IBMQ devices"
        )
    return info


@worker.task()
def backend_pass_from_info(
    backend_info: BackendInfo, optimisation_level: int = 2
) -> BasePass:
    return IBMQBackend.pass_from_info(
        backend_info, optimisation_level=optimisation_level
    )


@worker.task()
def backend_default_compilation_pass(
    device_name: str, optimisation_level: int = 2
) -> BasePass:
    backend = IBMQBackend(device_name)
    return backend.default_compilation_pass(optimisation_level)


@worker.task()
def fixed_pass(
    coupling_map: Sequence[tuple[int, int]],
    optimisation_level: int = 2,
) -> BasePass:
    arch = Architecture(coupling_map)
    return default_compilation_pass(optimisation_level, arch, IBMQ_GATE_SET)


@worker.task()
def compile(
    circuit: Circuit,
    device_name: str,
    optimisation_level: int = 2,
) -> Circuit:
    backend = IBMQBackend(device_name)
    compilation_pass = backend.default_compilation_pass(optimisation_level)
    compilation_pass.apply(circuit)
    return circuit


@worker.task()
def compile_circuit_ibmq(circuit: Circuit, device_name: str) -> Circuit:
    """Applies a predefined optimization pass for IBMQ devices.

    The optimization pass corresponds to a level=3 optimization.

    :param circuit: The original circuit.
    :type circuit: Circuit
    :return: The optimized circuit.
    :rtype: Circuit
    """
    p = IBMQBackend(device_name).default_compilation_pass()
    p.apply(circuit)
    return circuit


@worker.task()
def compile_circuits_ibmq(circuits: list[Circuit], device_name: str) -> list[Circuit]:
    """Applies a predefined optimization pass for IBMQ devices.

    :param circuits: A list of circuits to be optimized.
    :type circuits: list[Circuit]
    :return: The optimized circuits.
    :rtype: list[Circuit]
    """
    p = IBMQBackend(device_name).default_compilation_pass()
    for pytket_circuit in circuits:
        p.apply(pytket_circuit)
    return circuits


def main():
    worker.app(argv)


if __name__ == "__main__":
    main()
