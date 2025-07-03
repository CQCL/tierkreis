from dataclasses import dataclass
from datetime import datetime
import json
import random
from types import NoneType, UnionType
from typing import Callable, Sequence, Union, assert_never, get_args, get_origin


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


class TBytes(TRef):
    pass


_PType = bool | int | float | str | NoneType | Sequence["_PType"]
_TType = TBool | TInt | TFloat | TStr | TNone | TList["_TType"]

PType = _PType | bytes
TType = _TType | TBytes


WorkerFunction = Callable[..., PType]


def ttype_from_ptype(ptype: type[PType]) -> type[TType]:
    """Runtime conversion from type[PType] to type[TType]."""
    if get_origin(ptype) == UnionType or get_origin(ptype) == Union:
        args = tuple([ttype_from_ptype(x) for x in get_args(ptype)])
        return Union[args]  # type: ignore

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
    elif get_origin(ptype) == list or issubclass(ptype, Sequence):
        return TList[ttype_from_ptype(get_args(ptype)[0])]  # type: ignore
    else:
        assert_never(ptype)


def ptype_from_ttype(ttype: type[TType]) -> type[PType]:
    if get_origin(ttype) == UnionType or get_origin(ttype) == Union:
        args = tuple([ptype_from_ttype(x) for x in get_args(ttype)])
        return Union[args]  # type: ignore

    if get_origin(ttype) == TList or issubclass(ttype, TList):
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
        case bool() | int() | float() | str() | NoneType() | list() | Sequence():
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
