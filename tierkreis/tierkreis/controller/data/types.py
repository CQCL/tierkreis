import collections.abc
from dataclasses import dataclass
import json
from types import NoneType, UnionType
from typing import (
    Any,
    Callable,
    Generic,
    Sequence,
    TypeVarTuple,
    Union,
    assert_never,
    get_args,
    get_origin,
)
from tierkreis.controller.data.core import NodeIndex, PortID, ValueRef
from tierkreis.exceptions import TierkreisError
from typing_extensions import TypeIs


@dataclass
class TRef:
    node_index: int
    port_id: str

    def to_valueref(self) -> ValueRef:
        return (self.node_index, self.port_id)


class TBool(TRef):
    pass


class TInt(TRef):
    pass


class TFloat(TRef):
    pass


class TStr(TRef):
    pass


class TNone(TRef):
    pass


class TList[T](TRef):
    pass


TVT = TypeVarTuple("TVT")


class TTuple(TRef, Generic[*TVT]):
    pass


class TBytes(TRef):
    pass


_PType = bool | int | float | str | NoneType | Sequence["_PType"] | tuple["_PType", ...]
_TType = TBool | TInt | TFloat | TStr | TNone | TList["_TType"] | TTuple["_TType"]

PType = _PType | bytes


@dataclass
class TType[T: PType]:
    idx: NodeIndex
    port: PortID
    t: type[T] = T


x = TType[int](5, "7", int)
x.t

WorkerFunction = Callable[..., PType]


def is_union(o: object) -> bool:
    return get_origin(o) == UnionType or get_origin(o) == Union


def is_plist(ptype: object) -> TypeIs[type[Sequence[_PType]]]:
    return get_origin(ptype) == collections.abc.Sequence


def is_tlist(ttype: object) -> TypeIs[type[TList]]:
    return get_origin(ttype) == TList


def is_tuple(o: object) -> TypeIs[type[tuple[Any, ...]]]:
    return get_origin(o) == tuple


def is_ttuple(o: object) -> TypeIs[type[TTuple[Any]]]:
    return get_origin(o) == TTuple


def ttype_from_ptype(ptype: type[PType]) -> type[TType]:  # Used to format codegen
    """Runtime conversion from type[PType] to type[TType]."""
    if is_union(ptype):
        args = tuple([ttype_from_ptype(x) for x in get_args(ptype)])
        return Union[args]  # type: ignore

    elif is_tuple(ptype):
        args = [ttype_from_ptype(x) for x in get_args(ptype)]
        return TTuple[*args]

    elif is_plist(ptype):
        return TList[ttype_from_ptype(get_args(ptype)[0])]  # type: ignore

    if issubclass(ptype, bool):
        return TBool
    elif issubclass(ptype, int):
        return TInt
    elif issubclass(ptype, float):
        return TFloat
    elif issubclass(ptype, str):
        return TStr
    elif issubclass(ptype, NoneType):
        return TNone
    elif (
        issubclass(ptype, bytes)
        or issubclass(ptype, bytearray)
        or issubclass(ptype, memoryview)
    ):
        return TBytes

    else:
        assert_never(ptype)


def ptype_from_ttype(ttype: type[TType]) -> type[PType]:  # used in awkward g.const
    if is_union(ttype):
        args = tuple([ptype_from_ttype(x) for x in get_args(ttype)])
        return Union[args]  # type: ignore

    if is_ttuple(ttype):
        args = [ptype_from_ttype(x) for x in get_args(ttype)]
        return tuple[*args]

    if is_tlist(ttype):
        return Sequence[ptype_from_ttype(get_args(ttype)[0])]  # type: ignore

    if issubclass(ttype, TBool):
        return bool
    if issubclass(ttype, TInt):
        return int
    if issubclass(ttype, TFloat):
        return float
    if issubclass(ttype, TStr):
        return str
    if issubclass(ttype, TBytes):
        return bytes
    if issubclass(ttype, TNone):
        return NoneType
    else:
        assert_never(ttype)


def ptype_from_annotation(annotation: Any) -> type[PType]:
    try:
        if is_union(annotation):
            args = tuple([ptype_from_annotation(x) for x in get_args(annotation)])
            return Union[args]  # type: ignore

        elif is_tuple(annotation):
            args = [ptype_from_annotation(x) for x in get_args(annotation)]
            return tuple[*args]

        elif is_plist(annotation):
            return Sequence[ptype_from_annotation(get_args(annotation)[0])]  # type: ignore

        if issubclass(annotation, bool):
            return bool
        elif issubclass(annotation, int):
            return int
        elif issubclass(annotation, float):
            return float
        elif issubclass(annotation, str):
            return str
        elif issubclass(annotation, NoneType):
            return NoneType
        elif (
            issubclass(annotation, bytes)
            or issubclass(annotation, bytearray)
            or issubclass(annotation, memoryview)
        ):
            return bytes

        else:
            raise TierkreisError(f"Expected PType found {annotation}")
    except TypeError as exc:
        raise TierkreisError(f"Expected PType found {annotation}") from exc


def bytes_from_ptype(ptype: PType) -> bytes:
    match ptype:
        case bytes() | bytearray() | memoryview():
            return bytes(ptype)
        case (
            bool()
            | int()
            | float()
            | str()
            | NoneType()
            | collections.abc.Sequence()
            | tuple()
        ):
            return json.dumps(ptype).encode()
        case _:
            assert_never(ptype)


def ptype_from_bytes(bs: bytes, annotation: type[PType]) -> PType:
    if (
        issubclass(annotation, bool)
        or issubclass(annotation, int)
        or issubclass(annotation, float)
        or issubclass(annotation, str)
        or issubclass(annotation, NoneType)
    ):
        return json.loads(bs)
    elif (
        issubclass(annotation, bytes)
        or issubclass(annotation, bytearray)
        or issubclass(annotation, memoryview)
    ):
        return bs
    elif get_origin(annotation) == Sequence or issubclass(annotation, Sequence):
        return json.loads(bs)
    else:
        assert_never(annotation)


def format_ttype(ttype: type[TType]) -> str:
    if is_union(ttype):
        args = tuple([format_ttype(x) for x in get_args(ttype)])
        return " | ".join(args)

    if is_ttuple(ttype):
        args = [format_ttype(x) for x in get_args(ttype)]
        return f"TTuple[{", ".join(args)}]"

    if is_tlist(ttype):
        args = [format_ttype(x) for x in get_args(ttype)]
        return f"TList[{", ".join(args)}]"

    if (
        issubclass(ttype, TBool)
        or issubclass(ttype, TInt)
        or issubclass(ttype, TFloat)
        or issubclass(ttype, TStr)
        or issubclass(ttype, TBytes)
        or issubclass(ttype, TNone)
    ):
        return ttype.__qualname__

    assert_never(ttype)
