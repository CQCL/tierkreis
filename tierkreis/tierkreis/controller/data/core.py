from abc import abstractmethod
import json
from types import NoneType
from typing import (
    Any,
    Callable,
    NamedTuple,
    Protocol,
    Self,
    TypeGuard,
    assert_never,
    get_args,
    get_origin,
    runtime_checkable,
)

from tierkreis.exceptions import TierkreisError


@runtime_checkable
class DictConvertible(Protocol):
    @abstractmethod
    def to_dict(self) -> dict[str, Any]: ...

    @classmethod
    @abstractmethod
    def from_dict(cls, arg: dict[str, Any]) -> Self: ...


class X:

    def to_dict(self) -> dict[str, Any]:
        return {}

    @classmethod
    def from_dict(cls, arg: dict[str, Any]) -> "X":
        return X()


x: DictConvertible = X()

PortID = str
NodeIndex = int
ValueRef = tuple[NodeIndex, PortID]

TType = (
    # bool
    int
    | float
    | str
    | bytes
    | NoneType
    | list["TType"]
    | DictConvertible
)
TModel = tuple[TType, ...] | TType
WorkerFunction = Callable[..., TModel]


class EmptyModel(NamedTuple): ...


def bytes_from_ttype(t: TType) -> bytes:
    match t:
        case int() | float() | str() | NoneType():
            return json.dumps(t).encode()
        case bytes() | bytearray() | memoryview():
            return t
        case list():
            return json.dumps([bytes_from_ttype(x) for x in t]).encode()
        case DictConvertible():
            return json.dumps(t.to_dict()).encode()
        case _:
            assert_never(t)


def dict_from_tmodel(t: TModel) -> dict[str, TType]:
    match t:
        case tuple():
            d = getattr(t, "_asdict", None)
            if d is None:
                raise TierkreisError("")

            out: dict[str, TType] = {}
            for k, info in t.__annotations__.items():
                if info not in get_args(TType):
                    raise TierkreisError(f"Expected TType got {info}")
                out[k] = ttype_from_bytes(d[k], info)
            return out
        case _:
            return {"value": t}


def is_ttype(annotation: type) -> TypeGuard[type[TType]]:
    return (
        annotation is int
        or annotation is float
        or annotation is str
        or annotation is bytes
        or annotation is bytearray
        or annotation is memoryview
        or get_origin(annotation) == list  # need to take care of recursion
        or annotation is NoneType
        or isinstance(annotation, DictConvertible)
    )


def is_namedtuple_model(annotation: type) -> TypeGuard[tuple[TType, ...]]:
    if not hasattr(annotation, "_asdict"):
        return False

    if not hasattr(annotation, "_fields"):
        return False

    if not hasattr(annotation, "__annotations__"):
        return False

    for x in annotation.__annotations__.values():
        if not is_ttype(x):
            return False

    return True


def is_tmodel(annotation: type) -> TypeGuard[type[TModel]]:
    if is_namedtuple_model(annotation):
        return True

    if is_ttype(annotation):
        return True

    return False


def ttype_from_bytes(bs: bytes, annotation: type[TType]) -> TType:
    if issubclass(annotation, int):
        return int(json.loads(bs))
    elif issubclass(annotation, float):
        return float(json.loads(bs))
    elif issubclass(annotation, str):
        return str(json.loads(bs))
    elif issubclass(annotation, bytes):
        return bs
    elif issubclass(annotation, bytearray):
        return bs
    elif issubclass(annotation, memoryview):
        return bs
    elif issubclass(annotation, list) or get_origin(annotation) == list:
        return json.loads(bs)
    elif issubclass(annotation, DictConvertible):
        return annotation.from_dict(json.loads(bs))
    elif annotation is NoneType:
        return None
    else:
        assert_never(annotation)
