from base64 import b64encode
import collections.abc
import json
from types import NoneType
from typing import Any, TypeVar, assert_never

from pydantic import BaseModel
from tierkreis.controller.data.core import (
    DictConvertible,
    ListConvertible,
    NdarraySurrogate,
    PType,
    Struct,
)


class TierkreisEncoder(json.JSONEncoder):
    """Encode bytes also."""

    def default(self, o):
        if isinstance(o, bytes):
            return {"__tkr_bytes__": True, "bytes": b64encode(o).decode()}

        if isinstance(o, complex):
            return {"__tkr_complex__": [o.real, o.imag]}

        return super().default(o)


def ser_from_ptype(ptype: PType) -> Any:
    match ptype:
        case bytes() | bytearray() | memoryview():
            return bytes(ptype)
        case bool() | int() | float() | complex() | str() | NoneType() | TypeVar():
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
        case NdarraySurrogate():
            return ptype.dumps()
        case _:
            assert_never(ptype)


def bytes_from_ptype(ptype: PType) -> bytes:
    ser = ser_from_ptype(ptype)
    match ser:
        case bytes():
            return ser  # Top level bytes should be a clean pass-through.
        case _:
            return json.dumps(ser, cls=TierkreisEncoder).encode()
