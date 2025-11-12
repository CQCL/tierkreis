from sys import argv

from pytket._tket.circuit import Circuit
from pytket.backends.backendinfo import BackendInfo
from pytket.backends.backendresult import BackendResult
from pytket.extensions.quantinuum.backends.quantinuum import QuantinuumBackend
from pytket.passes import BasePass
from pytket.extensions.quantinuum.backends.api_wrappers import QuantinuumAPI
from pytket.extensions.quantinuum.backends.credential_storage import (
    QuantinuumConfigCredentialStorage,
)
from tierkreis import Worker
from tierkreis.exceptions import TierkreisError

from default_pass_quantinuum import default_compilation_pass

worker = Worker("quantinuum_worker")
api_handler = QuantinuumAPI(token_store=QuantinuumConfigCredentialStorage())


@worker.task()
def get_backend_info(device_name: str) -> BackendInfo:
    """Retrieves a BackendInfo object for a given device name.

    :param device_name: The name of the device.
    :type device_name: str
    :raises TierkreisError: If the device is not found or not accessible.
    :return: The BackendInfo object for the device.
    :rtype: BackendInfo
    """
    info = next(
        filter(
            lambda x: x.device_name == device_name,
            QuantinuumBackend.available_devices(api_handler=api_handler),
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
    """Returns a compilation pass according to the backend info.

    :param backend_info: Device information to use for compilation.
    :type backend_info: BackendInfo
    :param optimisation_level: The optimization level for the compilation, defaults to 2
    :type optimisation_level: int, optional
    :return: A compilation pass for the backend.
    :rtype: BasePass
    """
    return QuantinuumBackend.pass_from_info(
        backend_info, optimisation_level=optimisation_level
    )


@worker.task()
def backend_default_compilation_pass(
    device_name: str, optimisation_level: int = 2
) -> BasePass:
    """Returns the default compilation pass for a given device name.

    :param device_name: The name of the device.
    :type device_name: str
    :param optimisation_level: The optimization level for the compilation, defaults to 2
    :type optimisation_level: int, optional
    :return: The default compilation pass for the backend.
    :rtype: BasePass
    """
    backend = QuantinuumBackend(device_name, api_handler=api_handler)
    return backend.default_compilation_pass(optimisation_level)


@worker.task()
def fixed_pass() -> BasePass:
    """Returns a predefined compilation pass for Quantinuum devices.

    :return: The compilation pass.
    :rtype: BasePass
    """
    return default_compilation_pass()


@worker.task()
def compile(
    circuit: Circuit,
    device_name: str,
    optimisation_level: int = 2,
) -> Circuit:
    """Gets a compiled circuit for a given device name.

    :param circuit: The original circuit to compile.
    :type circuit: Circuit
    :param device_name: The name of the device to compile for.
    :type device_name: str
    :param optimisation_level: The optimization level for the compilation, defaults to 2
    :type optimisation_level: int, optional
    :return: The compiled circuit.
    :rtype: Circuit
    """
    backend = QuantinuumBackend(device_name, api_handler=api_handler)
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


@worker.task()
def run_circuit(circuit: Circuit, n_shots: int, device_name: str) -> BackendResult:
    """Submits a circuit to a Quantinuum backend and returns the result.

    :param circuit: The circuit to be run.
    :type circuit: Circuit
    :param n_shots: The number of shots to run.
    :type n_shots: int
    :return: The backend result.
    :rtype: BackendResult
    """
    backend = QuantinuumBackend(device_name, api_handler=api_handler)
    return backend.run_circuit(circuit, n_shots)


def main():
    worker.app(argv)


if __name__ == "__main__":
    main()
