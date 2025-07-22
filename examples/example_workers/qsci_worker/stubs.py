"""Code generated from qsci_worker namespace. Please do not edit."""

from typing import NamedTuple
from tierkreis.controller.data.models import TKR, OpaqueType


class state_prep(NamedTuple):
    ham_init: TKR[OpaqueType["__main__.Hamiltonian"]]  # noqa: F821 # fmt: skip
    reference_state: TKR[list[int]]  # noqa: F821 # fmt: skip
    max_iteration_prep: TKR[int]  # noqa: F821 # fmt: skip
    atol: TKR[float]  # noqa: F821 # fmt: skip
    mo_occ: TKR[list[int]]  # noqa: F821 # fmt: skip
    cas_init: TKR[OpaqueType["__main__.CompleteActiveSpace"]]  # noqa: F821 # fmt: skip
    cas_hsim: TKR[OpaqueType["__main__.CompleteActiveSpace"]]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[OpaqueType["pytket._tket.circuit.Circuit"]]]:  # noqa: F821 # fmt: skip
        return TKR[OpaqueType["pytket._tket.circuit.Circuit"]]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "qsci_worker"


class circuits_from_hamiltonians(NamedTuple):
    ham_init: TKR[OpaqueType["__main__.Hamiltonian"]]  # noqa: F821 # fmt: skip
    ham_hsim: TKR[OpaqueType["__main__.Hamiltonian"]]  # noqa: F821 # fmt: skip
    adapt_circuit: TKR[OpaqueType["pytket._tket.circuit.Circuit"]]  # noqa: F821 # fmt: skip
    t_step_list: TKR[list[float]]  # noqa: F821 # fmt: skip
    cas_init: TKR[OpaqueType["__main__.CompleteActiveSpace"]]  # noqa: F821 # fmt: skip
    cas_hsim: TKR[OpaqueType["__main__.CompleteActiveSpace"]]  # noqa: F821 # fmt: skip
    mo_occ: TKR[list[int]]  # noqa: F821 # fmt: skip
    max_cx_gates: TKR[int]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[list[OpaqueType["pytket._tket.circuit.Circuit"]]]]:  # noqa: F821 # fmt: skip
        return TKR[list[OpaqueType["pytket._tket.circuit.Circuit"]]]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "qsci_worker"


class energy_from_results(NamedTuple):
    ham_hsim: TKR[OpaqueType["__main__.Hamiltonian"]]  # noqa: F821 # fmt: skip
    backend_results: TKR[list[OpaqueType["pytket.backends.backendresult.BackendResult"]]]  # noqa: F821 # fmt: skip
    mo_occ: TKR[list[int]]  # noqa: F821 # fmt: skip
    cas_init: TKR[OpaqueType["__main__.CompleteActiveSpace"]]  # noqa: F821 # fmt: skip
    cas_hsim: TKR[OpaqueType["__main__.CompleteActiveSpace"]]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[float]]:  # noqa: F821 # fmt: skip
        return TKR[float]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "qsci_worker"
