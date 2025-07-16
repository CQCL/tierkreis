"""Code generated from chemistry_worker namespace. Please do not edit."""

from typing import NamedTuple, Sequence, Protocol
from tierkreis.controller.data.models import TKR, OpaqueType


class CompleteActiveSpace(Protocol):
    @property
    def n(self) -> int: ...  # noqa: F821 # fmt: skip
    @property
    def n_ele(self) -> int: ...  # noqa: F821 # fmt: skip


class Molecule(Protocol):
    @property
    def basis(self) -> str: ...  # noqa: F821 # fmt: skip
    @property
    def charge(self) -> int: ...  # noqa: F821 # fmt: skip
    @property
    def geometry(self) -> Sequence[tuple[str, Sequence[float]]]: ...  # noqa: F821 # fmt: skip


class make_ham(NamedTuple):
    molecule: TKR[Molecule]  # noqa: F821 # fmt: skip
    mo_occ: TKR[Sequence[int]]  # noqa: F821 # fmt: skip
    cas: TKR[CompleteActiveSpace]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[OpaqueType["__main__.Hamiltonian"]]]:  # noqa: F821 # fmt: skip
        return TKR[OpaqueType["__main__.Hamiltonian"]]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "chemistry_worker"
