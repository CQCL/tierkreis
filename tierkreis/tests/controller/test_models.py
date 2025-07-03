from types import NoneType
from typing import NamedTuple
import pytest
from tierkreis.controller.data.models import (
    PModel,
    TModel,
    model_equal,
    pmodel_from_tmodel,
    tmodel_from_pmodel,
)
from tierkreis.controller.data.types import (
    TBool,
    TBytes,
    TFloat,
    TInt,
    TList,
    TNone,
    TStr,
    TTuple,
)


class NamedPModel(NamedTuple):
    a: bool
    b: int
    c: float
    d: str
    e: NoneType
    f: list[str]
    g: bytes
    h: tuple[int, str]


class NamedTModel(NamedTuple):
    a: TBool
    b: TInt
    c: TFloat
    d: TStr
    e: TNone
    f: TList[TStr]
    g: TBytes
    h: TTuple[TInt, TStr]


params: list[tuple[type[PModel], type[TModel]]] = []
params.append((bool, TBool))
params.append((int, TInt))
params.append((float, TFloat))
params.append((str, TStr))
params.append((NoneType, TNone))
params.append((list[str], TList[TStr]))  #  type: ignore
params.append((bytes, TBytes))
params.append((tuple[int, str], TTuple[TInt, TStr]))  #  type: ignore
params.append((NamedPModel, NamedTModel))  #  type: ignore


@pytest.mark.parametrize("pmodel,tmodel", params)
def test_tmodel_from_pmodel(pmodel: type[PModel], tmodel: type[TModel]):
    assert model_equal(tmodel_from_pmodel(pmodel), tmodel)


@pytest.mark.parametrize("pmodel,tmodel", params)
def test_pmodel_from_tmodel(pmodel: type[PModel], tmodel: type[TModel]):
    assert model_equal(pmodel_from_tmodel(tmodel), pmodel)
