"""Code generated from builtins namespace. Please do not edit."""

from typing import NamedTuple
from tierkreis.controller.data.core import NodeIndex


class iadd(NamedTuple):
    a: int
    b: int

    @staticmethod
    def out(idx: NodeIndex) -> int:
        return (idx, "value")  # type:ignore # deliberately wrong

    @property
    def namespace(self) -> str:
        return "builtins"


class itimes(NamedTuple):
    a: int
    b: int

    @staticmethod
    def out(idx: NodeIndex) -> int:
        return (idx, "value")  # type:ignore # deliberately wrong

    @property
    def namespace(self) -> str:
        return "builtins"


class igt(NamedTuple):
    a: int
    b: int

    @staticmethod
    def out(idx: NodeIndex) -> bool:
        return (idx, "value")  # type:ignore # deliberately wrong

    @property
    def namespace(self) -> str:
        return "builtins"


class impl_and(NamedTuple):
    a: int
    b: int

    @staticmethod
    def out(idx: NodeIndex) -> bool:
        return (idx, "value")  # type:ignore # deliberately wrong

    @property
    def namespace(self) -> str:
        return "builtins"


class str_eq(NamedTuple):
    a: str
    b: str

    @staticmethod
    def out(idx: NodeIndex) -> bool:
        return (idx, "value")  # type:ignore # deliberately wrong

    @property
    def namespace(self) -> str:
        return "builtins"


class str_neq(NamedTuple):
    a: str
    b: str

    @staticmethod
    def out(idx: NodeIndex) -> bool:
        return (idx, "value")  # type:ignore # deliberately wrong

    @property
    def namespace(self) -> str:
        return "builtins"


class concat(NamedTuple):
    lhs: str
    rhs: str

    @staticmethod
    def out(idx: NodeIndex) -> str:
        return (idx, "value")  # type:ignore # deliberately wrong

    @property
    def namespace(self) -> str:
        return "builtins"


class mean(NamedTuple):
    values: bytes

    @staticmethod
    def out(idx: NodeIndex) -> float:
        return (idx, "value")  # type:ignore # deliberately wrong

    @property
    def namespace(self) -> str:
        return "builtins"
