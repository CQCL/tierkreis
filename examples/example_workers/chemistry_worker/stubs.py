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
    def geometry(self) -> Sequence[tuple[str, Sequence[float]]]: ...  # noqa: F821 # fmt: skip
    @property
    def charge(self) -> int: ...  # noqa: F821 # fmt: skip
    @property
    def basis(self) -> str: ...  # noqa: F821 # fmt: skip


# TODO: Manually added, need to add codegen that does the same.
class Hamiltonian(NamedTuple):
    h0: float
    h1: Sequence[Sequence[float]]
    h2: Sequence[Sequence[Sequence[Sequence[float]]]]


class make_ham(NamedTuple):
    molecule: TKR[Molecule]  # noqa: F821 # fmt: skip
    mo_occ: TKR[Sequence[int]]  # noqa: F821 # fmt: skip
    cas: TKR[CompleteActiveSpace]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[Hamiltonian]]:  # noqa: F821 # fmt: skip
        return TKR[Hamiltonian]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "chemistry_worker"
