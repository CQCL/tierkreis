"""Code generated from builtins namespace. Please do not edit."""

from typing import NamedTuple, Sequence
from tierkreis.controller.data.models import TKR


class iadd(NamedTuple):
    a: TKR[int]  # noqa: F821 # fmt: skip
    b: TKR[int]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[int]]:  # noqa: F821 # fmt: skip
        return TKR[int]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "builtins"


class itimes(NamedTuple):
    a: TKR[int]  # noqa: F821 # fmt: skip
    b: TKR[int]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[int]]:  # noqa: F821 # fmt: skip
        return TKR[int]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "builtins"


class igt(NamedTuple):
    a: TKR[int]  # noqa: F821 # fmt: skip
    b: TKR[int]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[bool]]:  # noqa: F821 # fmt: skip
        return TKR[bool]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "builtins"


class impl_and(NamedTuple):
    a: TKR[bool]  # noqa: F821 # fmt: skip
    b: TKR[bool]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[bool]]:  # noqa: F821 # fmt: skip
        return TKR[bool]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "builtins"


class str_eq(NamedTuple):
    a: TKR[str]  # noqa: F821 # fmt: skip
    b: TKR[str]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[bool]]:  # noqa: F821 # fmt: skip
        return TKR[bool]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "builtins"


class str_neq(NamedTuple):
    a: TKR[str]  # noqa: F821 # fmt: skip
    b: TKR[str]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[bool]]:  # noqa: F821 # fmt: skip
        return TKR[bool]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "builtins"


class concat(NamedTuple):
    lhs: TKR[str]  # noqa: F821 # fmt: skip
    rhs: TKR[str]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[str]]:  # noqa: F821 # fmt: skip
        return TKR[str]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "builtins"


class mean(NamedTuple):
    values: TKR[Sequence[float]]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[float]]:  # noqa: F821 # fmt: skip
        return TKR[float]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "builtins"
