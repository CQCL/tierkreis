from typing import Any, Callable, NamedTuple

from pydantic import BaseModel


Jsonable = Any
PortID = str
NodeIndex = int
ValueRef = tuple[NodeIndex, PortID]
ElementaryType = bool | int | float | str | bytes
TKType = ElementaryType | BaseModel


class TypedValueRef[T](NamedTuple):
    node_index: NodeIndex
    port: PortID

    @staticmethod
    def from_nodeindex(idx: NodeIndex, port: PortID = "value") -> "TypedValueRef[T]":
        return TypedValueRef[T](idx, port)


class Function[Out](BaseModel):
    namespace: str
    out: Callable[[NodeIndex], Out]


class EmptyModel(BaseModel):
    pass
