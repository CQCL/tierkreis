import collections.abc
from dataclasses import dataclass
import json
from types import NoneType, UnionType
from typing import Any, Sequence, Union, assert_never, get_args, get_origin
from typing_extensions import TypeIs


_PType = bool | int | float | str | NoneType | Sequence["_PType"] | tuple["_PType", ...]
PType = _PType | bytes


def _is_union(o: object) -> bool:
    return get_origin(o) == UnionType or get_origin(o) == Union


def _is_plist(ptype: object) -> TypeIs[type[Sequence[_PType]]]:
    return get_origin(ptype) == collections.abc.Sequence or get_origin(ptype) == list


def _is_tuple(o: object) -> TypeIs[type[tuple[Any, ...]]]:
    return get_origin(o) == tuple


def is_ptype(annotation: Any) -> TypeIs[type[PType]]:
    if _is_union(annotation):
        return all(is_ptype(x) for x in get_args(annotation))

    elif _is_tuple(annotation):
        return all(is_ptype(x) for x in get_args(annotation))

    elif _is_plist(annotation):
        return all(is_ptype(x) for x in get_args(annotation))

    elif annotation in get_args(PType):
        return True

    else:
        return False


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


def ptype_from_bytes(bs: bytes) -> PType:
    try:
        return json.loads(bs)
    except json.JSONDecodeError:
        return bs
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


def format_ptype(ptype: type[PType]) -> str:
    if _is_union(ptype):
        args = tuple([format_ptype(x) for x in get_args(ptype)])
        return " | ".join(args)

    if _is_tuple(ptype):
        args = [format_ptype(x) for x in get_args(ptype)]
        return f"tuple[{", ".join(args)}]"

    if _is_plist(ptype):
        args = [format_ptype(x) for x in get_args(ptype)]
        return f"Sequence[{", ".join(args)}]"

    if (
        issubclass(ptype, bool)
        or issubclass(ptype, int)
        or issubclass(ptype, float)
        or issubclass(ptype, str)
        or issubclass(ptype, bytes)
        or issubclass(ptype, NoneType)
    ):
        return ptype.__qualname__

    assert_never(ptype)
