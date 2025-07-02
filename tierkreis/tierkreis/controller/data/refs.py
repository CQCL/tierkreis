from types import NoneType
from typing import Any, Self, TypeGuard, assert_never, get_origin
from tierkreis.controller.data.core import (
    DictConvertible,
    NodeIndex,
    PortID,
    TType,
    ValueRef,
)
from tierkreis.exceptions import TierkreisError


class TRef:
    node_index: NodeIndex
    port_id: PortID

    def equal(self, value: "TRef") -> bool:
        return self.node_index == value.node_index and self.port_id == value.port_id

    def value_ref(self) -> tuple[NodeIndex, PortID]:
        return (self.node_index, self.port_id)


# The following doesn't work, which could be a problem...
# class BoolRef(bool, TRef): ...


class IntRef(int, TRef):
    @staticmethod
    def from_value_ref(node_index: NodeIndex, port_id: PortID = "value") -> "IntRef":
        x = IntRef()
        x.node_index = node_index
        x.port_id = port_id
        return x


class FloatRef(float, TRef):
    @staticmethod
    def from_value_ref(node_index: NodeIndex, port_id: PortID = "value") -> "FloatRef":
        x = FloatRef()
        x.node_index = node_index
        x.port_id = port_id
        return x


class StrRef(str, TRef):
    @staticmethod
    def from_value_ref(node_index: NodeIndex, port_id: PortID = "value") -> "StrRef":
        x = StrRef()
        x.node_index = node_index
        x.port_id = port_id
        return x


class BytesRef(bytes, TRef):
    @staticmethod
    def from_value_ref(node_index: NodeIndex, port_id: PortID = "value") -> "BytesRef":
        x = BytesRef()
        x.node_index = node_index
        x.port_id = port_id
        return x


class ListRef[T: TType](list[T], TRef):
    @staticmethod
    def from_value_ref(node_index: NodeIndex, port_id: PortID = "*") -> "ListRef[T]":
        x = ListRef[T]([])
        x.node_index = node_index
        x.port_id = port_id
        return x


class DictConvertibleRef[T: str](TRef):
    def to_dict(self) -> dict[str, Any]:
        return {}

    @classmethod
    def from_dict(cls, arg: dict[str, Any]) -> Self:
        return cls()

    @staticmethod
    def from_value_ref(
        node_index: NodeIndex, port_id: PortID = "*"
    ) -> "DictConvertibleRef[T]":
        x = DictConvertibleRef[T]()
        x.node_index = node_index
        x.port_id = port_id
        return x


class NoneRef(TRef):
    @staticmethod
    def from_value_ref(node_index: NodeIndex, port_id: PortID = "*") -> "NoneRef":
        x = NoneRef()
        x.node_index = node_index
        x.port_id = port_id
        return x


TypeRef = (
    IntRef
    | FloatRef
    | StrRef
    | BytesRef
    | ListRef["TypeRef"]
    | DictConvertibleRef[Any]
    | NoneRef
)
ModelRef = tuple[TypeRef, ...] | TypeRef


def is_typeref(t: TType) -> TypeGuard[TypeRef]:
    match t:
        case int():
            return isinstance(t, IntRef)
        case float():
            return isinstance(t, FloatRef)
        case str():
            return isinstance(t, StrRef)
        case bytes() | bytearray() | memoryview():
            return isinstance(t, BytesRef)
        case list():
            return isinstance(t, ListRef)
        case DictConvertible():
            return isinstance(t, DictConvertibleRef)
        case NoneType():
            return False
        case _:
            assert_never(t)


def reftype_from_ttype(t: type[TType]) -> type[TypeRef]:
    if issubclass(t, int):
        return IntRef
    elif issubclass(t, float):
        return FloatRef
    elif issubclass(t, str):
        return StrRef
    elif issubclass(t, bytes):
        return BytesRef
    elif issubclass(t, bytearray):
        return BytesRef
    elif issubclass(t, memoryview):
        return BytesRef
    elif issubclass(t, list) or get_origin(t) == list:
        return ListRef
    elif issubclass(t, DictConvertible):
        return DictConvertibleRef
    elif t is NoneType:
        return NoneRef
    else:
        assert_never(t)


def equal(ref1: ModelRef, ref2: ModelRef) -> bool:
    match ref1, ref2:
        case tuple(), tuple():
            return all(x.equal(y) for x, y in zip(ref1, ref2))
        case (tuple(), _) | (_, tuple()):
            return False
        case _:
            return ref1.equal(ref2)


def inputs_from_modelref(ref: ModelRef) -> dict[PortID, ValueRef]:
    match ref:
        case tuple():
            fields: list[str] | None = getattr(ref, "_fields", None)
            if fields is None:
                raise TierkreisError("TModel must be NamedTuple.")

            return {k: ref[i].value_ref() for i, k in enumerate(fields)}
        case _:
            return {"value": (ref.node_index, ref.port_id)}
