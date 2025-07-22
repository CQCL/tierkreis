"""Code generated from chemistry_worker namespace. Please do not edit."""

from typing import NamedTuple
from tierkreis.controller.data.models import TKR, OpaqueType


class make_ham(NamedTuple):
    molecule: TKR[OpaqueType["__main__.Molecule"]]  # noqa: F821 # fmt: skip
    mo_occ: TKR[list[int]]  # noqa: F821 # fmt: skip
    cas: TKR[OpaqueType["__main__.CompleteActiveSpace"]]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[OpaqueType["__main__.Hamiltonian"]]]:  # noqa: F821 # fmt: skip
        return TKR[OpaqueType["__main__.Hamiltonian"]]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "chemistry_worker"
