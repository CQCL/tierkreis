from types import NoneType
from typing import NamedTuple
import pytest
from tierkreis.controller.data.models import (
    PModel,
    TModel,
    dict_from_pmodel,
    model_equal,
    pmodel_from_tmodel,
    tmodel_from_pmodel,
)
from tierkreis.controller.data.types import (
    PType,
    TBool,
    TBytes,
    TFloat,
    TInt,
    TList,
    TNone,
    TStr,
    TTuple,
)
from tests.controller.test_types import type_pairs, ptypes


class NamedPModel(NamedTuple):
    a: bool
    b: int
    c: float
    d: str
    e: NoneType
    f: list[str]
    g: bytes
    h: tuple[int, str]
    i: list[list[int] | int]


class NamedTModel(NamedTuple):
    a: TBool
    b: TInt
    c: TFloat
    d: TStr
    e: TNone
    f: TList[TStr]
    g: TBytes
    h: TTuple[TInt, TStr]
    i: TList[TList[TInt] | TInt]


params: list[tuple[type[PModel], type[TModel]]] = []
params.extend(type_pairs)  # type: ignore
params.append((NamedPModel, NamedTModel))  #  type: ignore


@pytest.mark.parametrize("pmodel,tmodel", params)
def test_tmodel_from_pmodel(pmodel: type[PModel], tmodel: type[TModel]):
    assert model_equal(tmodel_from_pmodel(pmodel), tmodel)


@pytest.mark.parametrize("pmodel,tmodel", params)
def test_pmodel_from_tmodel(pmodel: type[PModel], tmodel: type[TModel]):
    assert model_equal(pmodel_from_tmodel(tmodel), pmodel)


@pytest.mark.parametrize("pmodel", ptypes)
def test_dict_from_pmodel_unnested(pmodel: PModel):
    assert dict_from_pmodel(pmodel) == {"value": pmodel}


named_p_model = NamedPModel(
    a=True,
    b=5,
    c=56.7,
    d="test",
    e=None,
    f=["one", "two", "three"],
    g=b"test bytes",
    h=(5, "test"),
    i=[[], 2],
)
named_p_model_expected = {
    "a": True,
    "b": 5,
    "c": 56.7,
    "d": "test",
    "e": None,
    "f": ["one", "two", "three"],
    "g": b"test bytes",
    "h": (5, "test"),
    "i": [[], 2],
}

pmodels = [(named_p_model, named_p_model_expected)]


@pytest.mark.parametrize("pmodel,expected", pmodels)
def test_dict_from_pmodel_nested(pmodel: PModel, expected: dict[str, PType]):
    assert dict_from_pmodel(pmodel) == expected
