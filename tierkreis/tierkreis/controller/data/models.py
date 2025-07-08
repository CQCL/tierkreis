from dataclasses import dataclass
from inspect import isclass
from typing import Protocol, SupportsIndex, runtime_checkable
from tierkreis.controller.data.core import NodeIndex, PortID, ValueRef
from tierkreis.controller.data.types import PType


@runtime_checkable
class PNamedModel(Protocol):
    def _asdict(self) -> dict[str, PType]: ...
    def __getitem__(self, key: SupportsIndex, /) -> PType: ...
    def __hash__(self) -> int: ...


PModel = PNamedModel | PType


@dataclass
class TKR[T: PModel]:
    node_index: NodeIndex
    port_id: PortID


@runtime_checkable
class TNamedModel(Protocol):
    def _asdict(self) -> dict[str, TKR[PType]]: ...
    def __getitem__(self, key: SupportsIndex, /) -> TKR[PType]: ...
    def __hash__(self) -> int: ...


TModel = TNamedModel | TKR


def dict_from_pmodel(pmodel: PModel) -> dict[PortID, PType]:
    if isinstance(pmodel, PNamedModel):
        return pmodel._asdict()

    return {"value": pmodel}


def dict_from_tmodel(tmodel: TModel) -> dict[PortID, ValueRef]:
    if isinstance(tmodel, TNamedModel):
        return {k: (v.node_index, v.port_id) for k, v in tmodel._asdict().items()}

    return {"value": (tmodel.node_index, tmodel.port_id)}


def model_fields(model: type[PModel] | type[TModel]) -> list[str]:
    if isclass(model) and isinstance(model, PNamedModel):
        return getattr(model, "_fields")

    if isclass(model) and isinstance(model, TNamedModel):
        return getattr(model, "_fields")

    return ["value"]


def init_tmodel[T: TModel](tmodel: type[T], refs: list[ValueRef]) -> T:
    if isclass(tmodel) and issubclass(tmodel, TNamedModel):
        args: list[TKR] = []
        for ref in refs:
            args.append(tmodel.__annotations__[ref[1]](ref[0], ref[1]))
        return tmodel(*args)
    return tmodel(refs[0][0], refs[0][1])
