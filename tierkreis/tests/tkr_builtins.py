"""Code generated from builtins namspace. Please do not edit."""

from typing import Callable, Literal
from pydantic import BaseModel
from tierkreis.controller.data.core import TypedValueRef, Function, NodeIndex


class iadd(Function[TypedValueRef[int]]):
    namespace: str = "builtins"
    a: TypedValueRef[int]
    b: TypedValueRef[int]

    out: Callable[[NodeIndex], TypedValueRef[int]] = TypedValueRef[int].from_nodeindex


class ciaddOutput(BaseModel):
    value: TypedValueRef[int]
    a: TypedValueRef[int]

    @staticmethod
    def from_nodeindex(n: NodeIndex) -> "ciaddOutput":
        return ciaddOutput(
            a=TypedValueRef[int](n, "a"), value=TypedValueRef[int](n, "value")
        )


class ciadd(Function[ciaddOutput]):
    namespace: str = "builtins"
    a: TypedValueRef[int]
    b: TypedValueRef[int]

    out: Callable[[NodeIndex], ciaddOutput] = ciaddOutput.from_nodeindex


class itimes(Function[TypedValueRef[int]]):
    namespace: str = "builtins"
    a: TypedValueRef[int]
    b: TypedValueRef[int]

    out: Callable[[NodeIndex], TypedValueRef[int]] = TypedValueRef[int].from_nodeindex


class igt(Function[TypedValueRef[bool]]):
    namespace: str = "builtins"
    a: TypedValueRef[int]
    b: TypedValueRef[int]

    out: Callable[[NodeIndex], TypedValueRef[bool]] = TypedValueRef[bool].from_nodeindex


class impl_and(Function[TypedValueRef[bool]]):
    namespace: str = "builtins"
    a: TypedValueRef[bool]
    b: TypedValueRef[bool]

    out: Callable[[NodeIndex], TypedValueRef[bool]] = TypedValueRef[bool].from_nodeindex


class str_eq(Function[TypedValueRef[bool]]):
    namespace: str = "builtins"
    a: TypedValueRef[str]
    b: TypedValueRef[str]

    out: Callable[[NodeIndex], TypedValueRef[bool]] = TypedValueRef[bool].from_nodeindex


class str_neq(Function[TypedValueRef[bool]]):
    namespace: str = "builtins"
    a: TypedValueRef[str]
    b: TypedValueRef[str]

    out: Callable[[NodeIndex], TypedValueRef[bool]] = TypedValueRef[bool].from_nodeindex


class concat(Function[TypedValueRef[str]]):
    namespace: str = "builtins"
    lhs: TypedValueRef[str]
    rhs: TypedValueRef[str]

    out: Callable[[NodeIndex], TypedValueRef[str]] = TypedValueRef[str].from_nodeindex
