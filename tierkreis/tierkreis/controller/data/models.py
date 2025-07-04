from typing import Any, NamedTuple
from tierkreis.controller.data.core import PortID
from tierkreis.exceptions import TierkreisError
from typing_extensions import TypeIs
from uuid import uuid4
from tierkreis.controller.data.types import (
    PType,
    TType,
    ptype_from_ttype,
    ttype_from_ptype,
)

PModel = tuple[PType, ...] | PType
TModel = tuple[TType, ...] | TType


def is_namedmodel(
    o: object,
) -> TypeIs[
    type[tuple[PType, ...]]
    | tuple[PType, ...]
    | type[tuple[TType, ...]]
    | tuple[TType, ...]
]:
    fields = getattr(o, "_fields", None)
    if fields is None:
        return False

    return True


def tmodel_from_pmodel(pmodel: type[PModel]) -> type[TModel]:
    if is_namedmodel(pmodel):
        types = [(k, ttype_from_ptype(v)) for k, v in pmodel.__annotations__.items()]
        NT = NamedTuple(f"{pmodel.__qualname__}{uuid4()}".replace("-", "_"), types)
        return NT

    return ttype_from_ptype(pmodel)


def pmodel_from_tmodel(tmodel: type[TModel]) -> type[PModel]:
    if is_namedmodel(tmodel):
        types = [(k, ptype_from_ttype(v)) for k, v in tmodel.__annotations__.items()]
        NT = NamedTuple(f"{tmodel.__qualname__}{uuid4()}".replace("-", "_"), types)
        return NT

    return ptype_from_ttype(tmodel)


def namedtuple_equal(
    x1: type[tuple[TType, ...] | tuple[PType, ...]],
    x2: type[tuple[TType, ...] | tuple[PType, ...]],
) -> bool:
    fields1 = getattr(x1, "_fields", None)
    fields2 = getattr(x2, "_fields", None)
    if fields1 is None or fields2 is None:
        raise TierkreisError("TModel or PModel should be NamedTuple.")

    for k in fields1:
        if k not in fields2:
            return False

        if x1.__annotations__[k] != x2.__annotations__[k]:
            return False

    return True


def model_equal(x1: type[TModel | PModel], x2: type[TModel | PModel]) -> bool:
    if is_namedmodel(x1) != is_namedmodel(x2):
        return False

    if is_namedmodel(x1) and is_namedmodel(x2):
        return namedtuple_equal(x1, x2)

    return x1 == x2


def dict_from_pmodel(pmodel: PModel) -> dict[PortID, PType]:
    if is_namedmodel(pmodel):
        asdict = getattr(pmodel, "_asdict", None)
        if asdict is None:
            raise TierkreisError("PModel should be NamedTuple")
        return asdict()

    return {"value": pmodel}
