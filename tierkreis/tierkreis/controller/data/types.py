import logging
from base64 import b64decode, b64encode
import collections.abc
from inspect import isclass
from itertools import chain
import json
from types import NoneType, UnionType
from typing import (
    Annotated,
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
from tierkreis.controller.data.core import RestrictedNamedTuple
from tierkreis.exceptions import TierkreisError
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


type Container[T] = (
    T
    | list[Container[T]]
    | Sequence[Container[T]]
    | tuple[Container[T], ...]
    | dict[str, Container[T]]
    | Mapping[str, Container[T]]
)
type ElementaryType = (
    bool
    | int
    | float
    | str
    | NoneType
    | bytes
    | DictConvertible
    | ListConvertible
    | BaseModel
)
type JsonType = Container[ElementaryType]
logger = logging.getLogger(__name__)


@runtime_checkable
class Struct(RestrictedNamedTuple[JsonType], Protocol): ...


_StructPType = JsonType | Struct
PType = Container[_StructPType]
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
    return (
        get_origin(o) == UnionType
        or get_origin(o) == Union
        or o == Union
        or o == UnionType
    )


def _is_generic(o) -> TypeIs[type[TypeVar]]:
    return isinstance(o, TypeVar)


def _is_list(ptype: object) -> TypeIs[type[Sequence[PType]]]:
    return get_origin(ptype) == collections.abc.Sequence or get_origin(ptype) is list


def _is_mapping(ptype: object) -> TypeIs[type[Mapping[str, PType]]]:
    return get_origin(ptype) is collections.abc.Mapping or get_origin(ptype) is dict


def _is_tuple(o: object) -> TypeIs[type[tuple[Any, ...]]]:
    return get_origin(o) is tuple


def is_ptype(annotation: Any) -> TypeIs[type[PType]]:
    if get_origin(annotation) is Annotated:
        return is_ptype(get_args(annotation)[0])

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
        annotation, (DictConvertible, ListConvertible, BaseModel, Struct)
    ):
        return True

    elif annotation in get_args(ElementaryType.__value__):
        return True

    origin = get_origin(annotation)
    if origin is not None:
        return is_ptype(origin) and all(is_ptype(x) for x in get_args(annotation))

    else:
        return False


def ser_from_ptype(ptype: PType) -> Any | bytes:
    match ptype:
        case bytes() | bytearray() | memoryview():
            # Top level bytes should be a clean pass-through.
            return bytes(ptype)
        case bool() | int() | float() | str() | NoneType() | TypeVar():
            return ptype
        case Struct():
            return {k: ser_from_ptype(p) for k, p in ptype._asdict().items()}
        case collections.abc.Sequence():
            return [ser_from_ptype(p) for p in ptype]
        case collections.abc.Mapping():
            return {k: ser_from_ptype(p) for k, p in ptype.items()}
        case DictConvertible():
            return ser_from_ptype(ptype.to_dict())
        case ListConvertible():
            return ser_from_ptype(ptype.to_list())
        case BaseModel():
            return ptype.model_dump(mode="json")
        case _:
            assert_never(ptype)


def bytes_from_ptype(ptype: PType) -> bytes:
    ser = ser_from_ptype(ptype)
    match ptype:
        case bytes():
            # Top level bytes should be a clean pass-through.
            return ptype
        case _:
            return json.dumps(ser, cls=TierkreisEncoder).encode()


def coerce_from_annotation[T: PType](ser: Any, annotation: type[T]) -> T:
    if get_origin(annotation) is Annotated:
        return coerce_from_annotation(ser, get_args(annotation)[0])

    if _is_union(annotation):
        for t in get_args(annotation):
            try:
                return coerce_from_annotation(ser, t)
            except AssertionError:
                logger.info(f"Tried deserialising as {t}")
        raise TierkreisError(f"Could not deserialise {ser} as {annotation}")

    origin = get_origin(annotation)
    if origin is None:
        origin = annotation

    if isinstance(origin, TypeVar):
        # Required to support generic parameters in functions,
        # we can't really make a judgement about what type it
        # should be deserialised in this case and so have to
        # just return the value in its "raw" form.
        return ser

    if issubclass(origin, (bool, int, float, str, bytes, NoneType)):
        return ser

    if issubclass(origin, DictConvertible):
        assert issubclass(annotation, origin)
        return annotation.from_dict(ser)

    if issubclass(origin, ListConvertible):
        assert issubclass(annotation, origin)
        return annotation.from_list(ser)

    if issubclass(origin, BaseModel):
        assert issubclass(annotation, origin)
        return annotation(**ser)

    if issubclass(origin, Struct):
        return cast(T, origin(**ser))

    if issubclass(origin, collections.abc.Sequence):
        args = get_args(annotation)
        if len(args) == 0:
            return ser

        return cast(T, [coerce_from_annotation(x, args[0]) for x in ser])

    if issubclass(origin, collections.abc.Mapping):
        args = get_args(annotation)
        if len(args) == 0:
            return ser

        return cast(T, {k: coerce_from_annotation(v, args[1]) for k, v in ser.items()})

    assert_never(ser)


def ptype_from_bytes[T: PType](bs: bytes, annotation: type[T] | None = None) -> T:
    if isclass(annotation) and issubclass(annotation, bytes):
        return cast(T, bs)

    try:
        j = json.loads(bs, cls=TierkreisDecoder)
    except json.JSONDecodeError as err:
        if annotation is None:
            return cast(T, bs)
        raise err

    if annotation is None:
        return j

    return coerce_from_annotation(j, annotation)


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

    if issubclass(ptype, (DictConvertible, ListConvertible, Struct)):
        return set()

    if issubclass(ptype, BaseModel):
        return set((str(x) for x in pydantic_get_args(ptype)))

    assert_never(ptype)
