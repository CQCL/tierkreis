from collections import namedtuple
from typing import Any, TypeGuard, assert_never
from uuid import uuid4
from tierkreis.controller.data.core import NodeIndex, PortID, TModel, TType
from tierkreis.controller.data.graph import Const, GraphData
from tierkreis.exceptions import TierkreisError


class TRef:
    node_index: NodeIndex
    port_id: PortID

    def equal(self, value: "TRef") -> bool:
        return self.node_index == value.node_index and self.port_id == value.port_id


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


TypeRef = IntRef | FloatRef | StrRef | BytesRef | ListRef["TypeRef"]
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
        case _:
            assert_never(t)


def typeref_from_ttype(g: GraphData, t: TType) -> TypeRef:
    if is_typeref(t):
        return t

    idx, port = g.add(Const(t))("value")
    match t:
        case int():
            return IntRef.from_value_ref(idx, port)
        case float():
            return FloatRef.from_value_ref(idx, port)
        case str():
            return StrRef.from_value_ref(idx, port)
        case bytes() | bytearray() | memoryview():
            return BytesRef.from_value_ref(idx, port)
        case list():
            return ListRef[Any].from_value_ref(idx, port)
        case _:
            assert_never(t)


def modelref_from_tmodel(g: GraphData, t: TModel) -> ModelRef:
    match t:
        case tuple():
            fields: list[str] | None = getattr(t, "_fields", None)
            if fields is None:
                raise TierkreisError("TModel must be NamedTuple.")

            NT = namedtuple(f"new_tuple_{uuid4().hex}", fields)  # pyright: ignore
            return NT(*[typeref_from_ttype(g, x) for x in t])

        case _:
            return typeref_from_ttype(g, t)


def equal(ref1: ModelRef, ref2: ModelRef) -> bool:
    match ref1, ref2:
        case tuple(), tuple():
            return all(x.equal(y) for x, y in zip(ref1, ref2))
        case (tuple(), _) | (_, tuple()):
            return False
        case _:
            return ref1.equal(ref2)
