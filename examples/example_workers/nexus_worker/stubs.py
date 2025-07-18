"""Code generated from nexus_worker namespace. Please do not edit."""

from typing import NamedTuple
from tierkreis.controller.data.models import TKR, OpaqueType


class submit(NamedTuple):
    circuits: TKR[list[OpaqueType["pytket._tket.circuit.Circuit"]]]  # noqa: F821 # fmt: skip
    n_shots: TKR[int]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[OpaqueType["qnexus.models.references.ExecuteJobRef"]]]:  # noqa: F821 # fmt: skip
        return TKR[OpaqueType["qnexus.models.references.ExecuteJobRef"]]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "nexus_worker"


class check_status(NamedTuple):
    execute_ref: TKR[OpaqueType["qnexus.models.references.ExecuteJobRef"]]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[str]]:  # noqa: F821 # fmt: skip
        return TKR[str]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "nexus_worker"


class get_results(NamedTuple):
    execute_ref: TKR[OpaqueType["qnexus.models.references.ExecuteJobRef"]]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[list[OpaqueType["pytket.backends.backendresult.BackendResult"]]]]:  # noqa: F821 # fmt: skip
        return TKR[list[OpaqueType["pytket.backends.backendresult.BackendResult"]]]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "nexus_worker"
