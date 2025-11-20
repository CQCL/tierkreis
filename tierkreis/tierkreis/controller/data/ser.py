from base64 import b64encode
import collections.abc
import json
from types import NoneType
from typing import Any, TypeVar, assert_never, get_args

from pydantic import BaseModel
from tierkreis.controller.data.core import (
    DictConvertible,
    ListConvertible,
    NdarraySurrogate,
    PType,
    Struct,
    get_serializer,
)


class TierkreisEncoder(json.JSONEncoder):
    """Encode bytes also."""

    def default(self, o):
        if isinstance(o, bytes):
            return {"__tkr_bytes__": True, "bytes": b64encode(o).decode()}

        if isinstance(o, complex):
            return {"__tkr_complex__": [o.real, o.imag]}

        return super().default(o)


def ser_from_ptype(ptype: PType, hint: type | None) -> Any:
    if sr := get_serializer(hint):
        return sr.serializer(ptype)

    match ptype:
        case bytes() | bytearray() | memoryview():
            return bytes(ptype)
        case bool() | int() | float() | complex() | str() | NoneType() | TypeVar():
            return ptype
        case Struct():
            return {
                k: ser_from_ptype(p, hint.__annotations__[k])
                for k, p in ptype._asdict().items()
            }
        case tuple():
            args = get_args(hint)
            if not args:
                return tuple([ser_from_ptype(p, None) for p in ptype])
            return tuple([ser_from_ptype(p, args[i]) for i, p in enumerate(ptype)])
        case collections.abc.Sequence():
            h = get_args(hint)[0] if hint else None
            return [ser_from_ptype(p, h) for p in ptype]
        case collections.abc.Mapping():
            h = get_args(hint)[1] if hint else None
            return {k: ser_from_ptype(p, h) for k, p in ptype.items()}
        case DictConvertible():
            return ser_from_ptype(ptype.to_dict(), None)
        case ListConvertible():
            return ser_from_ptype(ptype.to_list(), None)
        case BaseModel():
            return ptype.model_dump(mode="json")
        case NdarraySurrogate():
            return ptype.dumps()
        case _:
            assert_never(ptype)


def bytes_from_ptype(ptype: PType, hint: type | None = None) -> bytes:
    ser = ser_from_ptype(ptype, hint)
    match ser:
        case bytes():
            return ser  # Top level bytes should be a clean pass-through.
        case _:
            return json.dumps(ser, cls=TierkreisEncoder).encode()
