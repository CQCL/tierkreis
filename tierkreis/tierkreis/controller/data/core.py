from dataclasses import dataclass
from types import NoneType
from typing import (
    Any,
    Callable,
    Mapping,
    NamedTuple,
    Protocol,
    Self,
    Sequence,
    runtime_checkable,
)

from pydantic import BaseModel
from tierkreis.exceptions import TierkreisError


@runtime_checkable
class DictConvertible(Protocol):
    def to_dict(self) -> dict[str, Any]: ...
    @classmethod
    def from_dict(cls, arg: dict[str, Any]) -> Self: ...


Jsonable = Any
PortID = str
NodeIndex = int
ValueRef = tuple[NodeIndex, PortID]
TKRType = (
    bool
    | int
    | float
    | str
    | bytes
    | NoneType
    | Sequence["TKRType"]
    | Mapping[str, "TKRType"]
    | BaseModel
    | DictConvertible
)


class TKRRef[T: TKRType](NamedTuple):
    node_index: NodeIndex
    port: PortID

    @staticmethod
    def from_nodeindex(idx: NodeIndex, port: PortID = "value") -> "TKRRef[T]":
        return TKRRef[T](idx, port)

    def _to_dict(self) -> dict[str, Any]:
        return {"value": self}


TKRModel = tuple[TKRRef[TKRType], ...] | TKRRef[TKRType]


@dataclass
class TKRGlob[T: TKRModel]:
    t: T

    def map[S: TKRModel](self, f: Callable[[T], S]) -> "TKRGlob[S]":
        return TKRGlob(f(self.t))


class EmptyModel(NamedTuple): ...


def annotations_from_tkrref(ref: TKRModel) -> dict[str, Any]:
    if hasattr(ref, "_to_dict"):
        return ref._to_dict()  # type: ignore

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
    @property
    def namespace(self) -> str: ...

    @staticmethod
    def out(idx: NodeIndex) -> Out: ...
