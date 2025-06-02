"""Code generated from builtins namspace. Please do not edit."""

from typing import Callable
from pydantic import BaseModel
from tierkreis.controller.data.core import TypedValueRef, Function, ValueRef


class iadd(Function[TypedValueRef[int]]):
    a: TypedValueRef[int]
    b: TypedValueRef[int]

    out: Callable[[ValueRef], TypedValueRef[int]] = TypedValueRef[int].from_valueref


class ciaddOutput(BaseModel):
    value: TypedValueRef[int]
    a: TypedValueRef[int]

    @staticmethod
    def from_valueref(ref: ValueRef) -> "ciaddOutput":
        n = ref[0]
        return ciaddOutput(
            a=TypedValueRef[int](n, "a"), value=TypedValueRef[int](n, "value")
        )


class ciadd(Function[ciaddOutput]):
    a: TypedValueRef[int]
    b: TypedValueRef[int]

    out: Callable[[ValueRef], ciaddOutput] = ciaddOutput.from_valueref


class itimes(Function[TypedValueRef[int]]):
    a: TypedValueRef[int]
    b: TypedValueRef[int]

    out: Callable[[ValueRef], TypedValueRef[int]] = TypedValueRef[int].from_valueref


class igt(Function[TypedValueRef[bool]]):
    a: TypedValueRef[int]
    b: TypedValueRef[int]

    out: Callable[[ValueRef], TypedValueRef[bool]] = TypedValueRef[bool].from_valueref


class impl_and(Function[TypedValueRef[bool]]):
    a: TypedValueRef[bool]
    b: TypedValueRef[bool]

    out: Callable[[ValueRef], TypedValueRef[bool]] = TypedValueRef[bool].from_valueref


class str_eq(Function[TypedValueRef[bool]]):
    a: TypedValueRef[str]
    b: TypedValueRef[str]

    out: Callable[[ValueRef], TypedValueRef[bool]] = TypedValueRef[bool].from_valueref


class str_neq(Function[TypedValueRef[bool]]):
    a: TypedValueRef[str]
    b: TypedValueRef[str]

    out: Callable[[ValueRef], TypedValueRef[bool]] = TypedValueRef[bool].from_valueref


class concat(Function[TypedValueRef[str]]):
    lhs: TypedValueRef[str]
    rhs: TypedValueRef[str]

    out: Callable[[ValueRef], TypedValueRef[str]] = TypedValueRef[str].from_valueref
