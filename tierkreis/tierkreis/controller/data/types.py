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
from typing_extensions import TypeIs


@dataclass
class TRef:
    node_index: int
    port_id: str


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


_PType = bool | int | float | str | NoneType | list["_PType"] | tuple["_PType", ...]
_TType = TBool | TInt | TFloat | TStr | TNone | TList["_TType"] | TTuple["_TType"]

PType = _PType | bytes
TType = _TType | TBytes


WorkerFunction = Callable[..., PType]


def is_union(o: object) -> bool:
    return get_origin(o) == UnionType or get_origin(o) == Union


def is_plist(ptype: object) -> TypeIs[type[list[_PType]]]:
    return get_origin(ptype) == list


def is_tlist(ttype: object) -> TypeIs[type[TList]]:
    return get_origin(ttype) == TList


def is_ptuple(o: object) -> TypeIs[type[tuple[Any, ...]]]:
    return get_origin(o) == tuple


def is_ttuple(o: object) -> TypeIs[type[TTuple[Any]]]:
    return get_origin(o) == TTuple


def ttype_from_ptype(ptype: type[PType]) -> type[TType]:
    """Runtime conversion from type[PType] to type[TType]."""
    if is_union(ptype):
        args = tuple([ttype_from_ptype(x) for x in get_args(ptype)])
        return Union[args]  # type: ignore

    elif is_ptuple(ptype):
        args = [ttype_from_ptype(x) for x in get_args(ptype)]
        return TTuple[*args]

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
    elif is_plist(ptype):
        return TList[ttype_from_ptype(get_args(ptype)[0])]  # type: ignore
    else:
        assert_never(ptype)


def ptype_from_ttype(ttype: type[TType]) -> type[PType]:
    if is_union(ttype):
        args = tuple([ptype_from_ttype(x) for x in get_args(ttype)])
        return Union[args]  # type: ignore

    if is_ttuple(ttype):
        args = [ptype_from_ttype(x) for x in get_args(ttype)]
        return tuple[*args]

    if is_tlist(ttype):
        return list[ptype_from_ttype(get_args(ttype)[0])]  # type: ignore

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


def bytes_from_ptype(ptype: PType) -> bytes:
    match ptype:
        case bytes() | bytearray() | memoryview():
            return bytes(ptype)
        case bool() | int() | float() | str() | NoneType() | list() | tuple():
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
    elif get_origin(annotation) == list or issubclass(annotation, Sequence):
        return json.loads(bs)
    else:
        assert_never(annotation)
