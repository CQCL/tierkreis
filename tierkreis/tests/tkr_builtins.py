"""Code generated from builtins namspace. Please do not edit."""

from typing import Literal, NamedTuple
from tierkreis.controller.data.core import TKRRef, Function, NodeIndex


class iadd(Function[TKRRef[int]]):
    namespace: str = "builtins"
    a: TKRRef[int]
    b: TKRRef[int]

    @staticmethod
    def out(idx: NodeIndex) -> TKRRef[int]:
        return TKRRef[int].from_nodeindex(idx)


class ciaddOutput(NamedTuple):
    value: TKRRef[Literal["CIAddOutInner"]]
    a: TKRRef[int]

    @staticmethod
    def from_nodeindex(n: NodeIndex) -> "ciaddOutput":
        return ciaddOutput(
            a=TKRRef[int](n, "a"), value=TKRRef[Literal["CIAddOutInner"]](n, "value")
        )


class ciadd(Function[ciaddOutput]):
    namespace: str = "builtins"
    a: TKRRef[int]
    b: TKRRef[int]

    @staticmethod
    def out(idx: NodeIndex) -> ciaddOutput:
        return ciaddOutput.from_nodeindex(idx)


class itimes(Function[TKRRef[int]]):
    namespace: str = "builtins"
    a: TKRRef[int]
    b: TKRRef[int]

    @staticmethod
    def out(idx: NodeIndex) -> TKRRef[int]:
        return TKRRef[int].from_nodeindex(idx)


class igt(Function[TKRRef[bool]]):
    namespace: str = "builtins"
    a: TKRRef[int]
    b: TKRRef[int]

    @staticmethod
    def out(idx: NodeIndex) -> TKRRef[bool]:
        return TKRRef[bool].from_nodeindex(idx)


class impl_and(Function[TKRRef[bool]]):
    namespace: str = "builtins"
    a: TKRRef[bool]
    b: TKRRef[bool]

    @staticmethod
    def out(idx: NodeIndex) -> TKRRef[bool]:
        return TKRRef[bool].from_nodeindex(idx)


class str_eq(Function[TKRRef[bool]]):
    namespace: str = "builtins"
    a: TKRRef[str]
    b: TKRRef[str]

    @staticmethod
    def out(idx: NodeIndex) -> TKRRef[bool]:
        return TKRRef[bool].from_nodeindex(idx)


class str_neq(Function[TKRRef[bool]]):
    namespace: str = "builtins"
    a: TKRRef[str]
    b: TKRRef[str]

    @staticmethod
    def out(idx: NodeIndex) -> TKRRef[bool]:
        return TKRRef[bool].from_nodeindex(idx)


class concat(Function[TKRRef[str]]):
    namespace: str = "builtins"
    lhs: TKRRef[str]
    rhs: TKRRef[str]

    @staticmethod
    def out(idx: NodeIndex) -> TKRRef[str]:
        return TKRRef[str].from_nodeindex(idx)
