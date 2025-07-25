"""Code generated from chemistry_worker namespace. Please do not edit."""

from typing import NamedTuple, Protocol
from tierkreis.controller.data.models import TKR
from tierkreis.controller.data.types import Struct


class Molecule(Struct, Protocol):
    @property
    def basis(self) -> str: ...  # noqa: F821 # fmt: skip
    @property
    def geometry(self) -> list[tuple[str, list[float]]]: ...  # noqa: F821 # fmt: skip
    @property
    def charge(self) -> int: ...  # noqa: F821 # fmt: skip


class Hamiltonian(Struct, Protocol):
    @property
    def h1(self) -> list[list[float]]: ...  # noqa: F821 # fmt: skip
    @property
    def h0(self) -> float: ...  # noqa: F821 # fmt: skip
    @property
    def h2(self) -> list[list[list[list[float]]]]: ...  # noqa: F821 # fmt: skip


class CompleteActiveSpace(Struct, Protocol):
    @property
    def n_ele(self) -> int: ...  # noqa: F821 # fmt: skip
    @property
    def n(self) -> int: ...  # noqa: F821 # fmt: skip


class make_ham(NamedTuple):
    molecule: TKR[Molecule]  # noqa: F821 # fmt: skip
    mo_occ: TKR[list[int]]  # noqa: F821 # fmt: skip
    cas: TKR[CompleteActiveSpace]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[Hamiltonian]]:  # noqa: F821 # fmt: skip
        return TKR[Hamiltonian]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "chemistry_worker"
