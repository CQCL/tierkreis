"""Code generated from builtins namespace. Please do not edit."""

from typing import NamedTuple
from tierkreis.controller.data.types import (
    TBool,
    TInt,
    TFloat,
    TStr,
    TList,
)


class iadd(NamedTuple):
    a: TInt
    b: TInt

    @staticmethod
    def out() -> type:
        return TInt

    @property
    def namespace(self) -> str:
        return "builtins"


class itimes(NamedTuple):
    a: TInt
    b: TInt

    @staticmethod
    def out() -> type:
        return TInt

    @property
    def namespace(self) -> str:
        return "builtins"


class igt(NamedTuple):
    a: TInt
    b: TInt

    @staticmethod
    def out() -> type:
        return TBool

    @property
    def namespace(self) -> str:
        return "builtins"


class impl_and(NamedTuple):
    a: TBool
    b: TBool

    @staticmethod
    def out() -> type:
        return TBool

    @property
    def namespace(self) -> str:
        return "builtins"


class str_eq(NamedTuple):
    a: TStr
    b: TStr

    @staticmethod
    def out() -> type:
        return TBool

    @property
    def namespace(self) -> str:
        return "builtins"


class str_neq(NamedTuple):
    a: TStr
    b: TStr

    @staticmethod
    def out() -> type:
        return TBool

    @property
    def namespace(self) -> str:
        return "builtins"


class concat(NamedTuple):
    lhs: TStr
    rhs: TStr

    @staticmethod
    def out() -> type:
        return TStr

    @property
    def namespace(self) -> str:
        return "builtins"


class mean(NamedTuple):
    values: TList[TFloat]

    @staticmethod
    def out() -> type:
        return TFloat

    @property
    def namespace(self) -> str:
        return "builtins"
