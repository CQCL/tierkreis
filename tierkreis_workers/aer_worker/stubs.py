"""Code generated from aer_worker namespace. Please do not edit."""

# ruff: noqa: F821
from typing import NamedTuple, Sequence
from tierkreis.controller.data.models import TKR, OpaqueType


class submit(NamedTuple):
    circuits: TKR[Sequence[OpaqueType["pytket._tket.circuit.Circuit"]]]
    n_shots: TKR[int]

    @staticmethod
    def out() -> type[
        TKR[Sequence[OpaqueType["pytket.backends.backendresult.BackendResult"]]]
    ]:
        return TKR[Sequence[OpaqueType["pytket.backends.backendresult.BackendResult"]]]

    @property
    def namespace(self) -> str:
        return "aer_worker"


class submit_single(NamedTuple):
    circuit: TKR[OpaqueType["pytket._tket.circuit.Circuit"]]
    n_shots: TKR[int]

    @staticmethod
    def out() -> type[TKR[OpaqueType["pytket.backends.backendresult.BackendResult"]]]:
        return TKR[OpaqueType["pytket.backends.backendresult.BackendResult"]]

    @property
    def namespace(self) -> str:
        return "aer_worker"
