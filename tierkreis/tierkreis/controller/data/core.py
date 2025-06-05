from dataclasses import dataclass
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


@dataclass
class TKList[T]:
    f: Callable[[PortID], T]

    def __call__(self, port_id: PortID) -> T:
        return self.f(port_id)


class EmptyModel(BaseModel):
    pass
