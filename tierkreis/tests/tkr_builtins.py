"""Code generated from builtins namspace. Please do not edit."""

from typing import Callable, NamedTuple
from tierkreis.controller.data.core import TKRRef, Function, NodeIndex


class iadd(Function[TKRRef[int]]):
    namespace: str = "builtins"
    a: TKRRef[int]
    b: TKRRef[int]

    out: Callable[[NodeIndex], TKRRef[int]] = TKRRef[int].from_nodeindex


class ciaddOutput(NamedTuple):
    a: TKRRef[int]
    value: TKRRef[int]

    @staticmethod
    def from_nodeindex(n: NodeIndex) -> "ciaddOutput":
        return ciaddOutput(value=TKRRef[int](n, "value"), a=TKRRef[int](n, "a"))


class ciadd(Function[ciaddOutput]):
    namespace: str = "builtins"
    a: TKRRef[int]
    b: TKRRef[int]

    out: Callable[[NodeIndex], ciaddOutput] = ciaddOutput.from_nodeindex


class itimes(Function[TKRRef[int]]):
    namespace: str = "builtins"
    a: TKRRef[int]
    b: TKRRef[int]

    out: Callable[[NodeIndex], TKRRef[int]] = TKRRef[int].from_nodeindex


class igt(Function[TKRRef[bool]]):
    namespace: str = "builtins"
    a: TKRRef[int]
    b: TKRRef[int]

    out: Callable[[NodeIndex], TKRRef[bool]] = TKRRef[bool].from_nodeindex


class impl_and(Function[TKRRef[bool]]):
    namespace: str = "builtins"
    a: TKRRef[bool]
    b: TKRRef[bool]

    out: Callable[[NodeIndex], TKRRef[bool]] = TKRRef[bool].from_nodeindex


class str_eq(Function[TKRRef[bool]]):
    namespace: str = "builtins"
    a: TKRRef[str]
    b: TKRRef[str]

    out: Callable[[NodeIndex], TKRRef[bool]] = TKRRef[bool].from_nodeindex


class str_neq(Function[TKRRef[bool]]):
    namespace: str = "builtins"
    a: TKRRef[str]
    b: TKRRef[str]

    out: Callable[[NodeIndex], TKRRef[bool]] = TKRRef[bool].from_nodeindex


class concat(Function[TKRRef[str]]):
    namespace: str = "builtins"
    lhs: TKRRef[str]
    rhs: TKRRef[str]

    out: Callable[[NodeIndex], TKRRef[str]] = TKRRef[str].from_nodeindex
