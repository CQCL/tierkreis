"""Code generated from pytket_worker namespace. Please do not edit."""

from typing import NamedTuple, Union
from types import NoneType
from tierkreis.controller.data.models import TKR, OpaqueType


class get_backend_info(NamedTuple):
    config: TKR[Union[OpaqueType["quantinuum_schemas.models.backend_config.AerConfig"], OpaqueType["quantinuum_schemas.models.backend_config.AerStateConfig"], OpaqueType["quantinuum_schemas.models.backend_config.AerUnitaryConfig"], OpaqueType["quantinuum_schemas.models.backend_config.BraketConfig"], OpaqueType["quantinuum_schemas.models.backend_config.QuantinuumConfig"], OpaqueType["quantinuum_schemas.models.backend_config.IBMQConfig"], OpaqueType["quantinuum_schemas.models.backend_config.IBMQEmulatorConfig"], OpaqueType["quantinuum_schemas.models.backend_config.ProjectQConfig"], OpaqueType["quantinuum_schemas.models.backend_config.QulacsConfig"], OpaqueType["quantinuum_schemas.models.backend_config.SeleneQuestConfig"], OpaqueType["quantinuum_schemas.models.backend_config.SeleneStimConfig"], OpaqueType["quantinuum_schemas.models.backend_config.SeleneLeanConfig"], OpaqueType["quantinuum_schemas.models.backend_config.SeleneCoinflipConfig"], OpaqueType["quantinuum_schemas.models.backend_config.SeleneClassicalReplayConfig"]]]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[OpaqueType["pytket.backends.backendinfo.BackendInfo"]]]:  # noqa: F821 # fmt: skip
        return TKR[OpaqueType["pytket.backends.backendinfo.BackendInfo"]]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "pytket_worker"


class compile_using_info(NamedTuple):
    circuit: TKR[OpaqueType["pytket._tket.circuit.Circuit"]]  # noqa: F821 # fmt: skip
    backend_info: TKR[OpaqueType["pytket.backends.backendinfo.BackendInfo"]]  # noqa: F821 # fmt: skip
    config: TKR[Union[OpaqueType["quantinuum_schemas.models.backend_config.AerConfig"], OpaqueType["quantinuum_schemas.models.backend_config.AerStateConfig"], OpaqueType["quantinuum_schemas.models.backend_config.AerUnitaryConfig"], OpaqueType["quantinuum_schemas.models.backend_config.BraketConfig"], OpaqueType["quantinuum_schemas.models.backend_config.QuantinuumConfig"], OpaqueType["quantinuum_schemas.models.backend_config.IBMQConfig"], OpaqueType["quantinuum_schemas.models.backend_config.IBMQEmulatorConfig"], OpaqueType["quantinuum_schemas.models.backend_config.ProjectQConfig"], OpaqueType["quantinuum_schemas.models.backend_config.QulacsConfig"], OpaqueType["quantinuum_schemas.models.backend_config.SeleneQuestConfig"], OpaqueType["quantinuum_schemas.models.backend_config.SeleneStimConfig"], OpaqueType["quantinuum_schemas.models.backend_config.SeleneLeanConfig"], OpaqueType["quantinuum_schemas.models.backend_config.SeleneCoinflipConfig"], OpaqueType["quantinuum_schemas.models.backend_config.SeleneClassicalReplayConfig"]]]  # noqa: F821 # fmt: skip
    optimisation_level: TKR[int] | None = None  # noqa: F821 # fmt: skip
    timeout: TKR[int] | None = None  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[OpaqueType["pytket._tket.circuit.Circuit"]]]:  # noqa: F821 # fmt: skip
        return TKR[OpaqueType["pytket._tket.circuit.Circuit"]]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "pytket_worker"


class ibmq_offline_pass(NamedTuple):
    backend_info: TKR[OpaqueType["pytket.backends.backendinfo.BackendInfo"]]  # noqa: F821 # fmt: skip
    optimisation_level: TKR[int] | None = None  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[OpaqueType["pytket._tket.passes.BasePass"]]]:  # noqa: F821 # fmt: skip
        return TKR[OpaqueType["pytket._tket.passes.BasePass"]]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "pytket_worker"


class quantinuum_offline_pass(NamedTuple):
    backend_info: TKR[OpaqueType["pytket.backends.backendinfo.BackendInfo"]]  # noqa: F821 # fmt: skip
    optimisation_level: TKR[int] | None = None  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[OpaqueType["pytket._tket.passes.BasePass"]]]:  # noqa: F821 # fmt: skip
        return TKR[OpaqueType["pytket._tket.passes.BasePass"]]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "pytket_worker"


class add_measure_all(NamedTuple):
    circuit: TKR[OpaqueType["pytket._tket.circuit.Circuit"]]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[OpaqueType["pytket._tket.circuit.Circuit"]]]:  # noqa: F821 # fmt: skip
        return TKR[OpaqueType["pytket._tket.circuit.Circuit"]]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "pytket_worker"


class append_pauli_measurement_impl(NamedTuple):
    circuit: TKR[OpaqueType["pytket._tket.circuit.Circuit"]]  # noqa: F821 # fmt: skip
    pauli_string: TKR[OpaqueType["pytket._tket.pauli.QubitPauliString"]]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[OpaqueType["pytket._tket.circuit.Circuit"]]]:  # noqa: F821 # fmt: skip
        return TKR[OpaqueType["pytket._tket.circuit.Circuit"]]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "pytket_worker"


class optimise_phase_gadgets(NamedTuple):
    circuit: TKR[OpaqueType["pytket._tket.circuit.Circuit"]]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[OpaqueType["pytket._tket.circuit.Circuit"]]]:  # noqa: F821 # fmt: skip
        return TKR[OpaqueType["pytket._tket.circuit.Circuit"]]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "pytket_worker"


class apply_pass(NamedTuple):
    circuit: TKR[OpaqueType["pytket._tket.circuit.Circuit"]]  # noqa: F821 # fmt: skip
    compiler_pass: TKR[OpaqueType["pytket._tket.passes.BasePass"]]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[OpaqueType["pytket._tket.circuit.Circuit"]]]:  # noqa: F821 # fmt: skip
        return TKR[OpaqueType["pytket._tket.circuit.Circuit"]]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "pytket_worker"


class compile(NamedTuple):
    circuit: TKR[Union[OpaqueType["pytket._tket.circuit.Circuit"], str, bytes]]  # noqa: F821 # fmt: skip
    input_format: TKR[str] | None = None  # noqa: F821 # fmt: skip
    optimisation_level: TKR[int] | None = None  # noqa: F821 # fmt: skip
    gate_set: TKR[Union[list[str], NoneType]] | None = None  # noqa: F821 # fmt: skip
    coupling_map: TKR[Union[list[tuple[int, int]], NoneType]] | None = None  # noqa: F821 # fmt: skip
    output_format: TKR[str] | None = None  # noqa: F821 # fmt: skip
    optimisation_pass: TKR[Union[OpaqueType["pytket._tket.passes.BasePass"], NoneType]] | None = None  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[Union[OpaqueType["pytket._tket.circuit.Circuit"], str, bytes]]]:  # noqa: F821 # fmt: skip
        return TKR[Union[OpaqueType["pytket._tket.circuit.Circuit"], str, bytes]]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "pytket_worker"


class compile_circuit_quantinuum(NamedTuple):
    circuit: TKR[OpaqueType["pytket._tket.circuit.Circuit"]]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[OpaqueType["pytket._tket.circuit.Circuit"]]]:  # noqa: F821 # fmt: skip
        return TKR[OpaqueType["pytket._tket.circuit.Circuit"]]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "pytket_worker"


class compile_circuits_quantinuum(NamedTuple):
    circuits: TKR[list[OpaqueType["pytket._tket.circuit.Circuit"]]]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[list[OpaqueType["pytket._tket.circuit.Circuit"]]]]:  # noqa: F821 # fmt: skip
        return TKR[list[OpaqueType["pytket._tket.circuit.Circuit"]]]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "pytket_worker"


class compile_tket_circuit_ibm(NamedTuple):
    circuit: TKR[OpaqueType["pytket._tket.circuit.Circuit"]]  # noqa: F821 # fmt: skip
    backend_name: TKR[str]  # noqa: F821 # fmt: skip
    optimisation_level: TKR[int] | None = None  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[OpaqueType["pytket._tket.circuit.Circuit"]]]:  # noqa: F821 # fmt: skip
        return TKR[OpaqueType["pytket._tket.circuit.Circuit"]]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "pytket_worker"


class compile_tket_circuits_ibm(NamedTuple):
    circuits: TKR[list[OpaqueType["pytket._tket.circuit.Circuit"]]]  # noqa: F821 # fmt: skip
    backend_name: TKR[str]  # noqa: F821 # fmt: skip
    optimisation_level: TKR[int] | None = None  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[list[OpaqueType["pytket._tket.circuit.Circuit"]]]]:  # noqa: F821 # fmt: skip
        return TKR[list[OpaqueType["pytket._tket.circuit.Circuit"]]]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "pytket_worker"


class compile_tket_circuit_quantinuum(NamedTuple):
    circuit: TKR[OpaqueType["pytket._tket.circuit.Circuit"]]  # noqa: F821 # fmt: skip
    backend_name: TKR[str]  # noqa: F821 # fmt: skip
    optimisation_level: TKR[int] | None = None  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[OpaqueType["pytket._tket.circuit.Circuit"]]]:  # noqa: F821 # fmt: skip
        return TKR[OpaqueType["pytket._tket.circuit.Circuit"]]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "pytket_worker"


class compile_tket_circuits_quantinuum(NamedTuple):
    circuits: TKR[list[OpaqueType["pytket._tket.circuit.Circuit"]]]  # noqa: F821 # fmt: skip
    backend_name: TKR[str]  # noqa: F821 # fmt: skip
    optimisation_level: TKR[int] | None = None  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[list[OpaqueType["pytket._tket.circuit.Circuit"]]]]:  # noqa: F821 # fmt: skip
        return TKR[list[OpaqueType["pytket._tket.circuit.Circuit"]]]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "pytket_worker"


class to_qasm_str(NamedTuple):
    circuit: TKR[OpaqueType["pytket._tket.circuit.Circuit"]]  # noqa: F821 # fmt: skip
    header: TKR[str] | None = None  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[str]]:  # noqa: F821 # fmt: skip
        return TKR[str]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "pytket_worker"


class from_gasm_str(NamedTuple):
    qasm: TKR[str]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[OpaqueType["pytket._tket.circuit.Circuit"]]]:  # noqa: F821 # fmt: skip
        return TKR[OpaqueType["pytket._tket.circuit.Circuit"]]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "pytket_worker"


class to_qir_bytes(NamedTuple):
    circuit: TKR[OpaqueType["pytket._tket.circuit.Circuit"]]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[bytes]]:  # noqa: F821 # fmt: skip
        return TKR[bytes]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "pytket_worker"


class from_qir_bytes(NamedTuple):
    qir: TKR[bytes]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[OpaqueType["pytket._tket.circuit.Circuit"]]]:  # noqa: F821 # fmt: skip
        return TKR[OpaqueType["pytket._tket.circuit.Circuit"]]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "pytket_worker"


class expectation(NamedTuple):
    backend_result: TKR[OpaqueType["pytket.backends.backendresult.BackendResult"]]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[float]]:  # noqa: F821 # fmt: skip
        return TKR[float]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "pytket_worker"


class n_qubits(NamedTuple):
    circuit: TKR[OpaqueType["pytket._tket.circuit.Circuit"]]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[int]]:  # noqa: F821 # fmt: skip
        return TKR[int]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "pytket_worker"
