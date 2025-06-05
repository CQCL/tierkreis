from typing import Any, Callable, NamedTuple

from pydantic import BaseModel
from tierkreis.exceptions import TierkreisError


Jsonable = Any
PortID = str
NodeIndex = int
ValueRef = tuple[NodeIndex, PortID]
ElementaryType = bool | int | float | str | bytes
TKType = ElementaryType | BaseModel


class TKRRef[T](NamedTuple):
    node_index: NodeIndex
    port: PortID

    @staticmethod
    def from_nodeindex(idx: NodeIndex, port: PortID = "value") -> "TKRRef[T]":
        return TKRRef[T](idx, port)

    def _todict(self) -> dict[str, Any]:
        return {"value": self}


TKRModel = tuple[TKRRef[Any], ...] | TKRRef[Any]


class EmptyModel(NamedTuple): ...


def annotations_from_tkrref(ref: TKRModel) -> dict[str, Any]:
    if hasattr(ref, "_todict"):
        return ref._todict()  # type: ignore

    if hasattr(ref, "_asdict"):
        return ref._asdict()  # type: ignore

    raise TierkreisError("Graph inputs and output types must be NamedTuples.")


def ref_from_tkr_type[T: TKRModel](
    ref: type[T],
    idx_fn: Callable[[PortID], NodeIndex],
    name_fn: Callable[[PortID], PortID] = lambda x: x,
) -> T:
    if issubclass(TKRRef, ref):
        return ref.from_nodeindex(idx_fn("value"), name_fn("value"))  # type: ignore

    fields = {
        name: info.from_nodeindex(idx_fn(name), name_fn(name))
        for name, info in ref.__annotations__.items()
    }

    return ref(**fields)


class Function[Out](BaseModel):
    namespace: str
    out: Callable[[NodeIndex], Out]
