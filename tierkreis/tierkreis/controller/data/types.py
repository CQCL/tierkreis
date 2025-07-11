from base64 import b64decode, b64encode
import collections.abc
import json
from types import NoneType, UnionType
from typing import Any, Mapping, Sequence, Union, assert_never, get_args, get_origin
from typing_extensions import TypeIs


type _PType = (
    bool
    | int
    | float
    | str
    | NoneType
    | Sequence["_PType"]
    | tuple["_PType", ...]
    | Mapping[str, "_PType"]
)
PType = _PType | bytes

import json


class TierkreisEncoder(json.JSONEncoder):
    """Encode bytes also."""

    def default(self, o):
        if isinstance(o, bytes):
            return {"__tkr_bytes__": True, "bytes": b64encode(o).decode()}

        return super().default(o)


class TierkreisDecoder(json.JSONDecoder):
    """Decode bytes also."""

    def __init__(self, **kwargs):
        kwargs.setdefault("object_hook", self._object_hook)
        super().__init__(**kwargs)

    def _object_hook(self, d):
        """Try to decode a complex number."""
        if "__tkr_bytes__" in d and "bytes" in d:
            return b64decode(d["bytes"])
        return d


def _is_union(o: object) -> bool:
    return get_origin(o) == UnionType or get_origin(o) == Union


def _is_list(ptype: object) -> TypeIs[type[Sequence[_PType]]]:
    return get_origin(ptype) == collections.abc.Sequence or get_origin(ptype) is list


def _is_mapping(ptype: object) -> TypeIs[type[Mapping[str, _PType]]]:
    return get_origin(ptype) == Mapping or get_origin(ptype) is dict


def _is_tuple(o: object) -> TypeIs[type[tuple[Any, ...]]]:
    return get_origin(o) is tuple


def is_ptype(annotation: Any) -> TypeIs[type[PType]]:
    if _is_union(annotation):
        return all(is_ptype(x) for x in get_args(annotation))

    elif _is_tuple(annotation):
        return all(is_ptype(x) for x in get_args(annotation))

    elif _is_list(annotation):
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
            | dict()
            | Mapping()
        ):
            return json.dumps(ptype, cls=TierkreisEncoder).encode()
        case _:
            assert_never(ptype)


def ptype_from_bytes(bs: bytes) -> PType:
    try:
        return json.loads(bs, cls=TierkreisDecoder)
    except json.JSONDecodeError:
        return bs


def format_ptype(ptype: type[PType]) -> str:
    if _is_union(ptype):
        args = tuple([format_ptype(x) for x in get_args(ptype)])
        return " | ".join(args)

    if _is_tuple(ptype):
        args = [format_ptype(x) for x in get_args(ptype)]
        return f"tuple[{', '.join(args)}]"

    if _is_list(ptype):
        args = [format_ptype(x) for x in get_args(ptype)]
        return f"Sequence[{', '.join(args)}]"

    if _is_mapping(ptype):
        args = [format_ptype(x) for x in get_args(ptype)]
        return f"Mapping[{', '.join(args)}]"

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
