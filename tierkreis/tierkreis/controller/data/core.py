from typing import Any, Callable, NamedTuple, TypeVar

from pydantic import BaseModel


Jsonable = Any
PortID = str
NodeIndex = int
ValueRef = tuple[NodeIndex, PortID]
TKType = bool | int | float | str | bytes | BaseModel


class TypedValueRef[T](NamedTuple):
    node_index: NodeIndex
    port: PortID

    @staticmethod
    def from_valueref(ref: ValueRef) -> "TypedValueRef[T]":
        return TypedValueRef[T](ref[0], ref[1])


Out = TypeVar("Out", bound=TypedValueRef[Any] | dict[str, TypedValueRef[Any]])


class Function[Out](BaseModel):
    out: Callable[[Out], Any]
