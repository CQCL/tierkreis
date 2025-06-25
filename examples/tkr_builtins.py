"""Code generated from builtins namespace. Please do not edit."""

from typing import Literal, NamedTuple
import typing
from tierkreis.controller.data.core import TKRRef, Function, NodeIndex


class iadd(Function[TKRRef[int]]):
    a: TKRRef[int]
    b: TKRRef[int]

    @staticmethod
    def out(idx: NodeIndex) -> TKRRef[int]:
        return TKRRef[int].from_nodeindex(idx)

    @property
    def namespace(self) -> str:
        return "builtins"


class ciaddOutput(NamedTuple):
    value: TKRRef[Literal["CIAddOutInner"]]
    a: TKRRef[int]

    @staticmethod
    def from_nodeindex(n: NodeIndex) -> "ciaddOutput":
        return ciaddOutput(
            a=TKRRef[int](n, "a"), value=TKRRef[Literal["CIAddOutInner"]](n, "value")
        )


class ciadd(Function[ciaddOutput]):
    a: TKRRef[int]
    b: TKRRef[int]

    @staticmethod
    def out(idx: NodeIndex) -> ciaddOutput:
        return ciaddOutput.from_nodeindex(idx)

    @property
    def namespace(self) -> str:
        return "builtins"


class itimes(Function[TKRRef[int]]):
    a: TKRRef[int]
    b: TKRRef[int]

    @staticmethod
    def out(idx: NodeIndex) -> TKRRef[int]:
        return TKRRef[int].from_nodeindex(idx)

    @property
    def namespace(self) -> str:
        return "builtins"


class igt(Function[TKRRef[bool]]):
    a: TKRRef[int]
    b: TKRRef[int]

    @staticmethod
    def out(idx: NodeIndex) -> TKRRef[bool]:
        return TKRRef[bool].from_nodeindex(idx)

    @property
    def namespace(self) -> str:
        return "builtins"


class impl_and(Function[TKRRef[bool]]):
    a: TKRRef[bool]
    b: TKRRef[bool]

    @staticmethod
    def out(idx: NodeIndex) -> TKRRef[bool]:
        return TKRRef[bool].from_nodeindex(idx)

    @property
    def namespace(self) -> str:
        return "builtins"


class str_eq(Function[TKRRef[bool]]):
    a: TKRRef[str]
    b: TKRRef[str]

    @staticmethod
    def out(idx: NodeIndex) -> TKRRef[bool]:
        return TKRRef[bool].from_nodeindex(idx)

    @property
    def namespace(self) -> str:
        return "builtins"


class str_neq(Function[TKRRef[bool]]):
    a: TKRRef[str]
    b: TKRRef[str]

    @staticmethod
    def out(idx: NodeIndex) -> TKRRef[bool]:
        return TKRRef[bool].from_nodeindex(idx)

    @property
    def namespace(self) -> str:
        return "builtins"


class concat(Function[TKRRef[str]]):
    lhs: TKRRef[str]
    rhs: TKRRef[str]

    @staticmethod
    def out(idx: NodeIndex) -> TKRRef[str]:
        return TKRRef[str].from_nodeindex(idx)

    @property
    def namespace(self) -> str:
        return "builtins"


class mean(Function[TKRRef[float]]):
    values: TKRRef[typing.Sequence[float]]

    @staticmethod
    def out(idx: NodeIndex) -> TKRRef[float]:
        return TKRRef[float].from_nodeindex(idx)

    @property
    def namespace(self) -> str:
        return "builtins"
