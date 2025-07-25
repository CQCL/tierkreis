from dataclasses import dataclass
from inspect import isclass
from itertools import chain
from typing import (
    Literal,
    Protocol,
    cast,
    dataclass_transform,
    get_origin,
    overload,
    runtime_checkable,
)
from typing_extensions import TypeIs
from tierkreis.controller.data.core import (
    NodeIndex,
    PortID,
    RestrictedNamedTuple,
    ValueRef,
)
from tierkreis.controller.data.types import PType, generics_in_ptype

TKR_PORTMAPPING_FLAG = "__tkr_portmapping__"


@runtime_checkable
class PNamedModel(RestrictedNamedTuple[PType], Protocol):
    """A struct whose members are restricted to being PTypes.

    E.g. used to specify multiple outputs in Python worker code.
    """


@dataclass_transform()
def portmapping[T: PNamedModel](cls: type[T]) -> type[T]:
    setattr(cls, TKR_PORTMAPPING_FLAG, True)
    return cls


PModel = PNamedModel | PType
OpaqueType = Literal


@dataclass
class TKR[T: PModel]:
    node_index: NodeIndex
    port_id: PortID

    def value_ref(self) -> ValueRef:
        return (self.node_index, self.port_id)


@runtime_checkable
class TNamedModel(RestrictedNamedTuple[TKR[PType]], Protocol):
    """A struct whose members are restricted to being references to PTypes.

    E.g. in graph builder code these are outputs of tasks."""


TModel = TNamedModel | TKR


@overload
def is_portmapping(o: PModel) -> TypeIs[PNamedModel]: ...
@overload
def is_portmapping(o: type[PModel]) -> TypeIs[type[PNamedModel]]: ...
@overload
def is_portmapping(o: TModel) -> TypeIs[TNamedModel]: ...
@overload
def is_portmapping(o: type[TModel]) -> TypeIs[type[TNamedModel]]: ...
def is_portmapping(
    o,
) -> (
    TypeIs[type[PNamedModel]]
    | TypeIs[PNamedModel]
    | TypeIs[TNamedModel]
    | TypeIs[type[TNamedModel]]
):
    origin = get_origin(o)
    if origin is not None:
        return is_portmapping(origin)
    return hasattr(o, TKR_PORTMAPPING_FLAG)


def is_tnamedmodel(o) -> TypeIs[type[TNamedModel]]:
    origin = get_origin(o)
    if origin is not None:
        return is_tnamedmodel(origin)
    return isclass(o) and issubclass(o, TNamedModel)


def dict_from_pmodel(pmodel: PModel) -> dict[PortID, PType]:
    if is_portmapping(pmodel):
        return pmodel._asdict()

    return {"value": pmodel}


def dict_from_tmodel(tmodel: TModel) -> dict[PortID, ValueRef]:
    if isinstance(tmodel, TNamedModel):
        return {k: (v.node_index, v.port_id) for k, v in tmodel._asdict().items()}

    return {"value": (tmodel.node_index, tmodel.port_id)}


def model_fields(model: type[PModel] | type[TModel]) -> list[str]:
    if is_portmapping(model):
        return getattr(model, "_fields")

    if is_tnamedmodel(model):
        return getattr(model, "_fields")

    return ["value"]


def init_tmodel[T: TModel](tmodel: type[T], refs: list[ValueRef]) -> T:
    if is_tnamedmodel(tmodel):
        o = get_origin(tmodel)
        model = tmodel if not is_tnamedmodel(o) else o
        args: list[TKR] = []
        for ref in refs:
            key = ref[1].replace("-*", "")
            args.append(model.__annotations__[key](ref[0], ref[1]))
        return cast(T, model(*args))
    return tmodel(refs[0][0], refs[0][1])


def generics_in_pmodel(pmodel: type[PModel]) -> set[str]:
    if is_portmapping(pmodel):
        origin = get_origin(pmodel)
        if origin is not None:
            return generics_in_pmodel(origin)

        x = [generics_in_ptype(pmodel.__annotations__[t]) for t in model_fields(pmodel)]
        return set(chain(*x))

    return generics_in_ptype(pmodel)
