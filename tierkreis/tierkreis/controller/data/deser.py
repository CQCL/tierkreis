import logging
from base64 import b64decode
import collections.abc
from inspect import isclass
import json
import pickle
from types import NoneType
from typing import Annotated, Any, TypeVar, assert_never, cast, get_args, get_origin

from pydantic import BaseModel, ValidationError
from tierkreis.controller.data.core import (
    DictConvertible,
    ListConvertible,
    NdarraySurrogate,
    PType,
    Struct,
    _is_union,
)
from tierkreis.exceptions import TierkreisError


logger = logging.getLogger(__name__)


class TierkreisDecoder(json.JSONDecoder):
    """Decode bytes also."""

    def __init__(self, **kwargs):
        kwargs.setdefault("object_hook", self._object_hook)
        super().__init__(**kwargs)

    def _object_hook(self, d):
        """Try to decode an object containing bytes."""
        if "__tkr_bytes__" in d and "bytes" in d:
            return b64decode(d["bytes"])

        if "__tkr_complex__" in d:
            return complex(*d["__tkr_complex__"])

        return d


def coerce_from_annotation[T: PType](ser: Any, annotation: type[T] | None) -> T:
    if annotation is None:
        return ser

    if get_origin(annotation) is Annotated:
        return coerce_from_annotation(ser, get_args(annotation)[0])

    if _is_union(annotation):
        for t in get_args(annotation):
            try:
                return coerce_from_annotation(ser, t)
            except (AssertionError, ValidationError):
                logger.debug(f"Tried deserialising as {t}")
        raise TierkreisError(f"Could not deserialise {ser} as {annotation}")

    origin = get_origin(annotation)
    if origin is None:
        origin = annotation

    if ser is None:
        return ser

    if isinstance(origin, TypeVar):
        # Required to support generic parameters in functions,
        # we can't really make a judgement about what type it
        # should be deserialised in this case and so have to
        # just return the value in its "raw" form.
        return ser

    if issubclass(origin, (bool, int, float, complex, str, bytes, NoneType)):
        return ser

    if issubclass(origin, DictConvertible):
        assert issubclass(annotation, origin)
        return annotation.from_dict(ser)

    if issubclass(origin, ListConvertible):
        assert issubclass(annotation, origin)
        return annotation.from_list(ser)

    if issubclass(origin, NdarraySurrogate):
        return pickle.loads(ser)

    if issubclass(origin, BaseModel):
        assert issubclass(annotation, origin)
        return annotation(**ser)

    if issubclass(origin, Struct):
        d = {
            k: coerce_from_annotation(ser[k], v)
            for k, v in origin.__annotations__.items()
        }
        return cast(T, origin(**d))

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
    # Check if the type demmands a top-level pass-through. E.g. isn't JSON.
    if isclass(annotation) and issubclass(annotation, (bytes, NdarraySurrogate)):
        return coerce_from_annotation(bs, annotation)

    try:
        j = json.loads(bs, cls=TierkreisDecoder)
        return coerce_from_annotation(j, annotation)
    except (json.JSONDecodeError, UnicodeDecodeError) as err:
        if annotation is None:
            return cast(T, bs)
        raise err
