"""Code generated from pytket_simulators_worker namespace. Please do not edit."""

from typing import NamedTuple, Union
from types import NoneType
from tierkreis.controller.data.models import TKR, OpaqueType


class get_compiled_circuit(NamedTuple):
    circuit: TKR[OpaqueType["pytket._tket.circuit.Circuit"]]  # noqa: F821 # fmt: skip
    optimisation_level: TKR[Union[int, NoneType]]  # noqa: F821 # fmt: skip
    config: TKR[Union[OpaqueType["quantinuum_schemas.models.backend_config.AerConfig"], OpaqueType["quantinuum_schemas.models.backend_config.AerStateConfig"], OpaqueType["quantinuum_schemas.models.backend_config.AerUnitaryConfig"], OpaqueType["quantinuum_schemas.models.backend_config.BraketConfig"], OpaqueType["quantinuum_schemas.models.backend_config.QuantinuumConfig"], OpaqueType["quantinuum_schemas.models.backend_config.IBMQConfig"], OpaqueType["quantinuum_schemas.models.backend_config.IBMQEmulatorConfig"], OpaqueType["quantinuum_schemas.models.backend_config.ProjectQConfig"], OpaqueType["quantinuum_schemas.models.backend_config.QulacsConfig"], OpaqueType["quantinuum_schemas.models.backend_config.SeleneQuestConfig"], OpaqueType["quantinuum_schemas.models.backend_config.SeleneStimConfig"], OpaqueType["quantinuum_schemas.models.backend_config.SeleneLeanConfig"], OpaqueType["quantinuum_schemas.models.backend_config.SeleneCoinflipConfig"], OpaqueType["quantinuum_schemas.models.backend_config.SeleneClassicalReplayConfig"]]]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[OpaqueType["pytket._tket.circuit.Circuit"]]]:  # noqa: F821 # fmt: skip
        return TKR[OpaqueType["pytket._tket.circuit.Circuit"]]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "pytket_simulators_worker"


class run_circuit(NamedTuple):
    circuit: TKR[OpaqueType["pytket._tket.circuit.Circuit"]]  # noqa: F821 # fmt: skip
    n_shots: TKR[int]  # noqa: F821 # fmt: skip
    config: TKR[Union[OpaqueType["quantinuum_schemas.models.backend_config.AerConfig"], OpaqueType["quantinuum_schemas.models.backend_config.AerStateConfig"], OpaqueType["quantinuum_schemas.models.backend_config.AerUnitaryConfig"], OpaqueType["quantinuum_schemas.models.backend_config.BraketConfig"], OpaqueType["quantinuum_schemas.models.backend_config.QuantinuumConfig"], OpaqueType["quantinuum_schemas.models.backend_config.IBMQConfig"], OpaqueType["quantinuum_schemas.models.backend_config.IBMQEmulatorConfig"], OpaqueType["quantinuum_schemas.models.backend_config.ProjectQConfig"], OpaqueType["quantinuum_schemas.models.backend_config.QulacsConfig"], OpaqueType["quantinuum_schemas.models.backend_config.SeleneQuestConfig"], OpaqueType["quantinuum_schemas.models.backend_config.SeleneStimConfig"], OpaqueType["quantinuum_schemas.models.backend_config.SeleneLeanConfig"], OpaqueType["quantinuum_schemas.models.backend_config.SeleneCoinflipConfig"], OpaqueType["quantinuum_schemas.models.backend_config.SeleneClassicalReplayConfig"]]]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[OpaqueType["pytket.backends.backendresult.BackendResult"]]]:  # noqa: F821 # fmt: skip
        return TKR[OpaqueType["pytket.backends.backendresult.BackendResult"]]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "pytket_simulators_worker"


class run_circuits(NamedTuple):
    circuits: TKR[list[OpaqueType["pytket._tket.circuit.Circuit"]]]  # noqa: F821 # fmt: skip
    n_shots: TKR[list[int]]  # noqa: F821 # fmt: skip
    config: TKR[Union[OpaqueType["quantinuum_schemas.models.backend_config.AerConfig"], OpaqueType["quantinuum_schemas.models.backend_config.AerStateConfig"], OpaqueType["quantinuum_schemas.models.backend_config.AerUnitaryConfig"], OpaqueType["quantinuum_schemas.models.backend_config.BraketConfig"], OpaqueType["quantinuum_schemas.models.backend_config.QuantinuumConfig"], OpaqueType["quantinuum_schemas.models.backend_config.IBMQConfig"], OpaqueType["quantinuum_schemas.models.backend_config.IBMQEmulatorConfig"], OpaqueType["quantinuum_schemas.models.backend_config.ProjectQConfig"], OpaqueType["quantinuum_schemas.models.backend_config.QulacsConfig"], OpaqueType["quantinuum_schemas.models.backend_config.SeleneQuestConfig"], OpaqueType["quantinuum_schemas.models.backend_config.SeleneStimConfig"], OpaqueType["quantinuum_schemas.models.backend_config.SeleneLeanConfig"], OpaqueType["quantinuum_schemas.models.backend_config.SeleneCoinflipConfig"], OpaqueType["quantinuum_schemas.models.backend_config.SeleneClassicalReplayConfig"]]]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[list[OpaqueType["pytket.backends.backendresult.BackendResult"]]]]:  # noqa: F821 # fmt: skip
        return TKR[list[OpaqueType["pytket.backends.backendresult.BackendResult"]]]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "pytket_simulators_worker"
