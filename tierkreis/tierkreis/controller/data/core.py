from abc import ABC, abstractmethod
import collections.abc
from dataclasses import dataclass
from inspect import Parameter, _empty, isclass
from itertools import chain
from types import NoneType, UnionType
from typing import (
    Annotated,
    Any,
    Callable,
    Literal,
    Mapping,
    NamedTuple,
    Protocol,
    Self,
    Sequence,
    SupportsIndex,
    TypeVar,
    Union,
    assert_never,
    get_args,
    get_origin,
    runtime_checkable,
)
from typing_extensions import TypeIs

from pydantic import BaseModel
from pydantic._internal._generics import get_args as pydantic_get_args


PortID = str
NodeIndex = int
ValueRef = tuple[NodeIndex, PortID]
SerializationFormat = Literal["json", "bytes", "unknown"]


class EmptyModel(NamedTuple): ...


@runtime_checkable
class RestrictedNamedTuple[T](Protocol):
    """A NamedTuple whose members are restricted to being of type T."""

    def _asdict(self) -> dict[str, T]: ...
    def __getitem__(self, key: SupportsIndex, /) -> T: ...


@runtime_checkable
class NdarraySurrogate(Protocol):
    """A protocol to enable use of numpy.ndarray.

    By default the serialisation will be done using dumps
    and the deserialisation using `pickle.loads`."""

    def dumps(self) -> bytes: ...
    def tobytes(self) -> bytes: ...
    def tolist(self) -> list: ...


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


@dataclass
class Serializer:
    serializer: Callable[[Any], Any]
    serialization_format: SerializationFormat = "bytes"


@dataclass
class Deserializer:
    deserializer: Callable[[Any], Any]
    serialization_format: SerializationFormat = "bytes"


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
    | complex
    | str
    | NoneType
    | bytes
    | DictConvertible
    | ListConvertible
    | NdarraySurrogate
    | BaseModel
)
type JsonType = Container[ElementaryType]


@runtime_checkable
class Struct(RestrictedNamedTuple[JsonType], Protocol): ...


_StructPType = JsonType | Struct
PType = Container[_StructPType]
"""A restricted subset of Python types that can be used to annotate
worker functions for automatic codegen of graph builder stubs."""


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
        annotation,
        (DictConvertible, ListConvertible, NdarraySurrogate, BaseModel, Struct),
    ):
        return True

    elif annotation in get_args(ElementaryType.__value__):
        return True

    origin = get_origin(annotation)
    if origin is not None:
        return is_ptype(origin) and all(is_ptype(x) for x in get_args(annotation))

    else:
        return False


def generics_in_ptype(ptype: type[PType]) -> set[str]:
    if _is_generic(ptype):
        return {str(ptype)}

    if _is_union(ptype) or _is_tuple(ptype) or _is_list(ptype) or _is_mapping(ptype):
        return set(chain(*[generics_in_ptype(x) for x in get_args(ptype)]))

    origin = get_origin(ptype)
    if origin is not None:
        return generics_in_ptype(origin)

    if issubclass(ptype, (bool, int, float, complex, str, bytes, NoneType)):
        return set()

    if issubclass(ptype, (DictConvertible, ListConvertible, NdarraySurrogate, Struct)):
        return set()

    if issubclass(ptype, BaseModel):
        return set((str(x) for x in pydantic_get_args(ptype)))

    assert_never(ptype)


def has_default(t: Parameter) -> bool:
    return not (isclass(t.default) and issubclass(t.default, _empty))


def get_serializer(hint: type | None) -> Serializer | None:
    if hint is None:
        return None

    for arg in get_args(hint):
        if isinstance(arg, Serializer):
            return arg


def get_deserializer(hint: type | None) -> Deserializer | None:
    if hint is None:
        return None

    for arg in get_args(hint):
        if isinstance(arg, Deserializer):
            return arg
