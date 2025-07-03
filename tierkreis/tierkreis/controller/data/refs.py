from collections import namedtuple
from typing import get_args
from uuid import uuid4
from tierkreis.controller.data.core import TModel, TType, ValueRef


ModelRef = tuple[ValueRef, ...] | ValueRef


def modelref_from_tmodel_single(t: type[TType], refs: list[ValueRef]) -> ValueRef:
    return refs[0]


def modelref_from_tmodel_nested(
    t: type[tuple[TType, ...]], refs: list[ValueRef]
) -> tuple[ValueRef]:
    fields: list[str] | None = getattr(t, "_fields", None)
    if fields is None:
        fields = [str(x) for x in range(len(get_args(t)))]

    NT = namedtuple(f"{t.__qualname__}{uuid4()}".replace("-", "_"), fields)  # type: ignore
    return NT(*refs)


def modelref_from_tmodel(t: type[TModel], refs: list[ValueRef]) -> ModelRef:
    if issubclass(t, tuple):
        return modelref_from_tmodel_nested(t, refs)
    else:
        return modelref_from_tmodel_single(t, refs)
