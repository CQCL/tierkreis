import collections.abc
from dataclasses import dataclass
import json
from types import NoneType, UnionType
from typing import Any, Callable, Sequence, Union, assert_never, get_args, get_origin
from tierkreis.controller.data.core import NodeIndex, PortID
from tierkreis.exceptions import TierkreisError
from typing_extensions import TypeIs


_PType = bool | int | float | str | NoneType | Sequence["_PType"] | tuple["_PType", ...]
PType = _PType | bytes
WorkerFunction = Callable[..., PType]


@dataclass
class TKR[T: PType]:
    node_index: NodeIndex
    port_id: PortID


def is_union(o: object) -> bool:
    return get_origin(o) == UnionType or get_origin(o) == Union


def is_plist(ptype: object) -> TypeIs[type[Sequence[_PType]]]:
    return get_origin(ptype) == collections.abc.Sequence or get_origin(ptype) == list


def is_tuple(o: object) -> TypeIs[type[tuple[Any, ...]]]:
    return get_origin(o) == tuple


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


def format_ptype(ptype: type[PType]) -> str:
    if is_union(ptype):
        args = tuple([format_ptype(x) for x in get_args(ptype)])
        return " | ".join(args)

    if is_tuple(ptype):
        args = [format_ptype(x) for x in get_args(ptype)]
        return f"tuple[{", ".join(args)}]"

    if is_plist(ptype):
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
