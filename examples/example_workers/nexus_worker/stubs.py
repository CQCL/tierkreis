"""Code generated from nexus_worker namespace. Please do not edit."""

# ruff: noqa: F821
from typing import NamedTuple, Sequence
from tierkreis.controller.data.models import TKR, OpaqueType


class submit(NamedTuple):
    circuits: TKR[Sequence[OpaqueType["pytket._tket.circuit.Circuit"]]]
    n_shots: TKR[int]

    @staticmethod
    def out() -> type[TKR[OpaqueType["qnexus.models.references.ExecuteJobRef"]]]:
        return TKR[OpaqueType["qnexus.models.references.ExecuteJobRef"]]

    @property
    def namespace(self) -> str:
        return "nexus_worker"


class check_status(NamedTuple):
    execute_ref: TKR[OpaqueType["qnexus.models.references.ExecuteJobRef"]]

    @staticmethod
    def out() -> type[TKR[str]]:
        return TKR[str]

    @property
    def namespace(self) -> str:
        return "nexus_worker"


class get_results(NamedTuple):
    execute_ref: TKR[OpaqueType["qnexus.models.references.ExecuteJobRef"]]

    @staticmethod
    def out() -> type[
        TKR[Sequence[OpaqueType["pytket.backends.backendresult.BackendResult"]]]
    ]:
        return TKR[Sequence[OpaqueType["pytket.backends.backendresult.BackendResult"]]]

    @property
    def namespace(self) -> str:
        return "nexus_worker"
