"""Code generated from aer_worker namespace. Please do not edit."""

from typing import NamedTuple
from tierkreis.controller.data.models import TKR, OpaqueType


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
