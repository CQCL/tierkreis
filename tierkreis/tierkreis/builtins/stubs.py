"""Code generated from builtins namespace. Please do not edit."""

from typing import NamedTuple, Sequence
from tierkreis.controller.data.types import TKR


class iadd(NamedTuple):
    a: TKR[int]
    b: TKR[int]

    @staticmethod
    def out() -> type:
        return TKR[int]

    @property
    def namespace(self) -> str:
        return "builtins"


class itimes(NamedTuple):
    a: TKR[int]
    b: TKR[int]

    @staticmethod
    def out() -> type:
        return TKR[int]

    @property
    def namespace(self) -> str:
        return "builtins"


class igt(NamedTuple):
    a: TKR[int]
    b: TKR[int]

    @staticmethod
    def out() -> type:
        return TKR[bool]

    @property
    def namespace(self) -> str:
        return "builtins"


class impl_and(NamedTuple):
    a: TKR[bool]
    b: TKR[bool]

    @staticmethod
    def out() -> type:
        return TKR[bool]

    @property
    def namespace(self) -> str:
        return "builtins"


class str_eq(NamedTuple):
    a: TKR[str]
    b: TKR[str]

    @staticmethod
    def out() -> type:
        return TKR[bool]

    @property
    def namespace(self) -> str:
        return "builtins"


class str_neq(NamedTuple):
    a: TKR[str]
    b: TKR[str]

    @staticmethod
    def out() -> type:
        return TKR[bool]

    @property
    def namespace(self) -> str:
        return "builtins"


class concat(NamedTuple):
    lhs: TKR[str]
    rhs: TKR[str]

    @staticmethod
    def out() -> type:
        return TKR[str]

    @property
    def namespace(self) -> str:
        return "builtins"


class mean(NamedTuple):
    values: TKR[Sequence[float]]

    @staticmethod
    def out() -> type:
        return TKR[float]

    @property
    def namespace(self) -> str:
        return "builtins"
