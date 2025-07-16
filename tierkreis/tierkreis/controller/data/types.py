from base64 import b64decode, b64encode
import collections.abc
from inspect import isclass
from itertools import chain
import json
from types import NoneType, UnionType
from typing import (
    Any,
    Mapping,
    Protocol,
    Self,
    Sequence,
    TypeVar,
    Union,
    assert_never,
    cast,
    get_args,
    get_origin,
    runtime_checkable,
)
from pydantic import BaseModel
from pydantic._internal._generics import get_args as pydantic_get_args
from typing_extensions import TypeIs


@runtime_checkable
class DictConvertible(Protocol):
    def to_dict(self) -> dict: ...
    @classmethod
    def from_dict(cls, arg: dict, /) -> "Self": ...


@runtime_checkable
class ListConvertible(Protocol):
    def to_list(self) -> list: ...
    @classmethod
    def from_list(cls, arg: list, /) -> "Self": ...


type PType = (
    bool
    | int
    | float
    | str
    | NoneType
    | Sequence["PType"]
    | tuple["PType", ...]
    | Mapping[str, "PType"]
    | bytes
    | DictConvertible
    | ListConvertible
    | BaseModel
)
"""A restricted subset of Python types that can be used to annotate
worker functions for automatic codegen of graph builder stubs."""


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
        """Try to decode an object containing bytes."""
        if "__tkr_bytes__" in d and "bytes" in d:
            return b64decode(d["bytes"])
        return d


def _is_union(o: object) -> bool:
    return get_origin(o) == UnionType or get_origin(o) == Union


def _is_generic(o) -> TypeIs[type[TypeVar]]:
    return isinstance(o, TypeVar)


def _is_list(ptype: object) -> TypeIs[type[Sequence[PType]]]:
    return get_origin(ptype) == collections.abc.Sequence or get_origin(ptype) is list


def _is_mapping(ptype: object) -> TypeIs[type[Mapping[str, PType]]]:
    return get_origin(ptype) is collections.abc.Mapping or get_origin(ptype) is dict


def _is_tuple(o: object) -> TypeIs[type[tuple[Any, ...]]]:
    return get_origin(o) is tuple


def is_ptype(annotation: Any) -> TypeIs[type[PType]]:
    if _is_generic(annotation):
        return True

    if (
        _is_union(annotation)
        or _is_tuple(annotation)
        or _is_list(annotation)
        or _is_mapping(annotation)
    ):
        return all(is_ptype(x) for x in get_args(annotation))

    elif isclass(annotation) and issubclass(
        annotation, (DictConvertible, ListConvertible, BaseModel)
    ):
        return True

    elif annotation in get_args(PType.__value__):
        return True

    else:
        return False


def bytes_from_ptype(ptype: PType) -> bytes:
    match ptype:
        case bytes() | bytearray() | memoryview():
            # Top level bytes should be a clean pass-through.
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
            | collections.abc.Mapping()
            | TypeVar()
        ):
            return json.dumps(ptype, cls=TierkreisEncoder).encode()
        case DictConvertible():
            return json.dumps(ptype.to_dict(), cls=TierkreisEncoder).encode()
        case ListConvertible():
            return json.dumps(ptype.to_list(), cls=TierkreisEncoder).encode()
        case BaseModel():
            return ptype.model_dump_json().encode()
        case _:
            assert_never(ptype)


def ptype_from_bytes[T: PType](bs: bytes, annotation: type[T] | None = None) -> T:
    try:
        j = json.loads(bs, cls=TierkreisDecoder)
        if annotation is None:
            return j
        if isclass(annotation) and issubclass(annotation, DictConvertible):
            return annotation.from_dict(j)
        if isclass(annotation) and issubclass(annotation, ListConvertible):
            return annotation.from_list(j)
        if isclass(annotation) and issubclass(annotation, BaseModel):
            return annotation(**j)

        return j

    except json.JSONDecodeError:
        return cast(T, bs)


def generics_in_ptype(ptype: type[PType]) -> set[str]:
    if _is_generic(ptype):
        return {str(ptype)}

    if _is_union(ptype) or _is_tuple(ptype) or _is_list(ptype) or _is_mapping(ptype):
        return set(chain(*[generics_in_ptype(x) for x in get_args(ptype)]))

    origin = get_origin(ptype)
    if origin is not None:
        return generics_in_ptype(origin)

    if issubclass(ptype, (bool, int, float, str, bytes, NoneType)):
        return set()

    if issubclass(ptype, (DictConvertible, ListConvertible)):
        return set()

    if issubclass(ptype, BaseModel):
        return set((str(x) for x in pydantic_get_args(ptype)))

    assert_never(ptype)
