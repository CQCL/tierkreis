"""Code generated from aer_worker namespace. Please do not edit."""

from typing import NamedTuple, Union
from types import NoneType
from tierkreis.controller.data.models import TKR, OpaqueType


class get_compiled_circuit(NamedTuple):
    circuit: TKR[OpaqueType["pytket._tket.circuit.Circuit"]]  # noqa: F821 # fmt: skip
    optimisation_level: TKR[Union[int, NoneType]]  # noqa: F821 # fmt: skip
    timeout: TKR[Union[int, NoneType]]  # noqa: F821 # fmt: skip
    config: TKR[OpaqueType["quantinuum_schemas.models.backend_config.AerConfig"]]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[OpaqueType["pytket._tket.circuit.Circuit"]]]:  # noqa: F821 # fmt: skip
        return TKR[OpaqueType["pytket._tket.circuit.Circuit"]]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "aer_worker"


class run_circuit(NamedTuple):
    circuit: TKR[OpaqueType["pytket._tket.circuit.Circuit"]]  # noqa: F821 # fmt: skip
    n_shots: TKR[int]  # noqa: F821 # fmt: skip
    config: TKR[OpaqueType["quantinuum_schemas.models.backend_config.AerConfig"]]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[OpaqueType["pytket.backends.backendresult.BackendResult"]]]:  # noqa: F821 # fmt: skip
        return TKR[OpaqueType["pytket.backends.backendresult.BackendResult"]]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "aer_worker"


class run_circuits(NamedTuple):
    circuits: TKR[list[OpaqueType["pytket._tket.circuit.Circuit"]]]  # noqa: F821 # fmt: skip
    n_shots: TKR[list[int]]  # noqa: F821 # fmt: skip
    config: TKR[OpaqueType["quantinuum_schemas.models.backend_config.AerConfig"]]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[list[OpaqueType["pytket.backends.backendresult.BackendResult"]]]]:  # noqa: F821 # fmt: skip
        return TKR[list[OpaqueType["pytket.backends.backendresult.BackendResult"]]]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "aer_worker"


class to_qasm3_str(NamedTuple):
    circuit: TKR[OpaqueType["pytket._tket.circuit.Circuit"]]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[str]]:  # noqa: F821 # fmt: skip
        return TKR[str]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "aer_worker"


class submit(NamedTuple):
    circuits: TKR[list[OpaqueType["pytket._tket.circuit.Circuit"]]]  # noqa: F821 # fmt: skip
    n_shots: TKR[int]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[list[OpaqueType["pytket.backends.backendresult.BackendResult"]]]]:  # noqa: F821 # fmt: skip
        return TKR[list[OpaqueType["pytket.backends.backendresult.BackendResult"]]]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "aer_worker"


class submit_single(NamedTuple):
    circuit: TKR[OpaqueType["pytket._tket.circuit.Circuit"]]  # noqa: F821 # fmt: skip
    n_shots: TKR[int]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[OpaqueType["pytket.backends.backendresult.BackendResult"]]]:  # noqa: F821 # fmt: skip
        return TKR[OpaqueType["pytket.backends.backendresult.BackendResult"]]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "aer_worker"
