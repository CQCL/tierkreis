import json
from types import NoneType
from typing import (
    Any,
    Callable,
    NamedTuple,
    Protocol,
    Sequence,
    TypeGuard,
    get_args,
    get_origin,
)

from tierkreis.exceptions import TierkreisError


PortID = str
NodeIndex = int
ValueRef = tuple[NodeIndex, PortID]

TType = bool | int | float | str | bytes | NoneType | Sequence["TType"]
TModel = tuple[TType, ...] | TType
WorkerFunction = Callable[..., TModel]


class EmptyModel(NamedTuple): ...


class Function[Out: TModel](Protocol):
    @property
    def namespace(self) -> str: ...

    @staticmethod
    def out(idx: NodeIndex) -> Out: ...


class TierkreisEncoder(json.JSONEncoder):
    def default(self, o: Any) -> Any:
        if isinstance(o, (bytes, bytearray)):
            return {"__is_bytes__": True, "bytes": o.decode()}
        return super().default(o)


def tierkreis_decoder(o: dict[Any, Any]) -> Any:
    if "__is_bytes__" in o and "bytes" in o:
        return str(o["bytes"]).encode()
    return o


def bytes_from_ttype(t: TType) -> bytes:
    return json.dumps(t, cls=TierkreisEncoder).encode()


def ttype_from_bytes(bs: bytes) -> TType:
    return json.loads(bs, object_hook=tierkreis_decoder)


def fields_tmodel(t: type[TModel]) -> list[str]:
    if issubclass(t, int):
        return ["value"]
    elif issubclass(t, str):
        return ["value"]
    elif issubclass(t, float):
        return ["value"]
    elif issubclass(t, bytes):
        return ["value"]
    elif issubclass(t, bytearray):
        return ["value"]
    elif issubclass(t, memoryview):
        return ["value"]
    elif issubclass(t, list):
        return ["value"]
    elif issubclass(t, NoneType):
        return ["value"]
    elif issubclass(t, tuple):
        return getattr(t, "_fields", get_args(t))


def is_ttype(annotation: type) -> TypeGuard[type[TType]]:
    return (
        annotation is int
        or annotation is bool
        or annotation is float
        or annotation is str
        or annotation is bytes
        or annotation is bytearray
        or annotation is memoryview
        or get_origin(annotation) == list  # need to take care of recursion
        or annotation is NoneType
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


def dict_from_tmodel(t: TModel) -> dict[PortID, TType]:
    match t:
        case tuple():
            as_dict = getattr(t, "_asdict", None)
            if as_dict is None:
                raise TierkreisError("TModel should be NamedTuple.")
            return as_dict()
        case _:
            return {"value": t}
