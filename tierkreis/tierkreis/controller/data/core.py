from typing import Any, Callable, NamedTuple

from pydantic import BaseModel
from tierkreis.exceptions import TierkreisError


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

    def _todict(self) -> dict[str, Any]:
        return {"value": self}


TKRef = tuple[TypedValueRef[Any], ...]  # | TypedValueRef[Any]


def dict_from_tkref(ref: TKRef) -> dict[str, Any]:
    if not hasattr(ref, "_asdict"):
        raise TierkreisError("Graph inputs and output types must be NamedTuples.")
    return ref._asdict()  # type: ignore


class Function[Out](BaseModel):
    namespace: str
    out: Callable[[NodeIndex], Out]


class EmptyModel(NamedTuple):
    pass
