from dataclasses import dataclass
from inspect import isclass
from itertools import chain
from typing import (
    Literal,
    Protocol,
    SupportsIndex,
    get_origin,
    runtime_checkable,
)
from typing_extensions import TypeIs
from tierkreis.controller.data.core import NodeIndex, PortID, ValueRef
from tierkreis.controller.data.types import PType, generics_in_ptype


@runtime_checkable
class PNamedModel(Protocol):
    """A struct whose members are restricted to being PTypes.

    E.g. used to specify multiple outputs in Python worker code.
    """

    def _asdict(self) -> dict[str, PType]: ...
    def __getitem__(self, key: SupportsIndex, /) -> PType: ...


PModel = PNamedModel | PType
OpaqueType = Literal


@dataclass
class TKR[T: PModel]:
    node_index: NodeIndex
    port_id: PortID


@runtime_checkable
class TNamedModel(Protocol):
    """A struct whose members are restricted to being references to PTypes.

    E.g. in graph builder code these are outputs of tasks."""

    def _asdict(self) -> dict[str, TKR[PType]]: ...
    def __getitem__(self, key: SupportsIndex, /) -> TKR[PType]: ...


TModel = TNamedModel | TKR


def is_pnamedmodel(o) -> TypeIs[type[PNamedModel]]:
    origin = get_origin(o)
    if origin is not None:
        return is_pnamedmodel(origin)
    return isclass(o) and issubclass(o, PNamedModel)


def is_tnamedmodel(o) -> TypeIs[type[TNamedModel] | TNamedModel]:
    origin = get_origin(o)
    if origin is not None:
        return is_tnamedmodel(origin)
    return (isclass(o) and issubclass(o, TNamedModel)) or (isinstance(o, TNamedModel))


def dict_from_pmodel(pmodel: PModel) -> dict[PortID, PType]:
    if isinstance(pmodel, PNamedModel):
        return pmodel._asdict()

    return {"value": pmodel}


def dict_from_tmodel(tmodel: TModel) -> dict[PortID, ValueRef]:
    if is_tnamedmodel(tmodel):
        return {k: (v.node_index, v.port_id) for k, v in tmodel._asdict().items()}

    return {"value": (tmodel.node_index, tmodel.port_id)}


def model_fields(model: type[PModel] | type[TModel]) -> list[str]:
    if is_pnamedmodel(model):
        return getattr(model, "_fields")

    if is_tnamedmodel(model):
        return getattr(model, "_fields")

    return ["value"]


def init_tmodel[T: TModel](tmodel: type[T], refs: list[ValueRef]) -> T:
    if is_tnamedmodel(tmodel):
        origin = get_origin(tmodel)
        if origin is not None:
            tmodel = origin
        args: list[TKR] = []
        for ref in refs:
            key = ref[1].replace("-*", "")
            args.append(tmodel.__annotations__[key](ref[0], ref[1]))
        return tmodel(*args)
    return tmodel(refs[0][0], refs[0][1])


def generics_in_pmodel(pmodel: type[PModel]) -> set[str]:
    if is_pnamedmodel(pmodel):
        origin = get_origin(pmodel)
        if origin is not None:
            return generics_in_pmodel(origin)

        x = [generics_in_ptype(pmodel.__annotations__[t]) for t in model_fields(pmodel)]
        return set(chain(*x))

    return generics_in_ptype(pmodel)
