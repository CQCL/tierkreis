from typing import Any, NamedTuple, Protocol, SupportsIndex, runtime_checkable
from tierkreis.controller.data.core import PortID, ValueRef
from tierkreis.exceptions import TierkreisError
from uuid import uuid4
from tierkreis.controller.data.types import (
    PType,
    TType,
    ptype_from_ttype,
    ttype_from_ptype,
)


@runtime_checkable
class PNamedModel(Protocol):
    @property
    def _fields(self) -> tuple[str, ...]: ...
    def _asdict(self) -> dict[str, PType]: ...
    def __getitem__(self, key: SupportsIndex, /) -> PType: ...


@runtime_checkable
class TNamedModel(Protocol):
    @property
    def _fields(self) -> tuple[str, ...]: ...
    def _asdict(self) -> dict[str, TType]: ...
    def __getitem__(self, key: SupportsIndex, /) -> TType: ...


PModel = PNamedModel | PType
TModel = TNamedModel | TType


def tmodel_from_pmodel(pmodel: type[PModel]) -> type[TModel]:
    if issubclass(pmodel, PNamedModel):
        types = [(k, ttype_from_ptype(v)) for k, v in pmodel.__annotations__.items()]
        NT = NamedTuple(f"{pmodel.__qualname__}{uuid4()}".replace("-", "_"), types)
        return NT

    return ttype_from_ptype(pmodel)


def pmodel_from_tmodel(tmodel: type[TModel]) -> type[PModel]:
    if issubclass(tmodel, TNamedModel):
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


def dict_from_pmodel(pmodel: PModel) -> dict[PortID, PType]:
    if isinstance(pmodel, PNamedModel):
        return pmodel._asdict()

    return {"value": pmodel}


def dict_from_tmodel(tmodel: TModel) -> dict[PortID, ValueRef]:
    if isinstance(tmodel, TNamedModel):
        return {k: (v.node_index, v.port_id) for k, v in tmodel._asdict().items()}

    return {"value": (tmodel.node_index, tmodel.port_id)}


def model_fields(model: type[PModel]) -> list[str]:
    if isinstance(model, PNamedModel):
        return getattr(model, "_fields")
    return ["value"]


def init_tmodel[T: TModel](tmodel: type[T], refs: list[ValueRef]) -> T:
    if issubclass(tmodel, TNamedModel):
        args: list[TType] = []
        for ref in refs:
            args.append(tmodel.__annotations__[ref[1]](ref[0], ref[1]))
        return tmodel(*args)  # type: ignore # we know that this is NamedTuple
    return tmodel(refs[0][0], refs[0][1])
