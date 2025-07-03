from types import NoneType, UnionType
import pytest
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
    TType,
    bytes_from_ptype,
    ptype_from_bytes,
    ptype_from_ttype,
    ttype_from_ptype,
)


params: list[tuple[type[PType] | UnionType, type[TType] | UnionType]] = []
params.append((bool, TBool))
params.append((int, TInt))
params.append((str, TStr))
params.append((float, TFloat))
params.append((NoneType, TNone))
params.append((bytes, TBytes))
params.append((list[str], TList[TStr]))  #  type: ignore
params.append((list[list[list[NoneType]]], TList[TList[TList[TNone]]]))  #  type: ignore
params.append((list[str | list[int]], TList[TStr | TList[TInt]]))  #  type: ignore
params.append(
    (list[str | list[int | float]], TList[TStr | TList[TInt | TFloat]])  #  type: ignore
)
params.append((int | None, TInt | TNone))
params.append((int | bytes, TInt | TBytes))
params.append((tuple[int, str], TTuple[TInt, TStr]))  #  type: ignore
params.append((tuple[int | str], TTuple[TInt | TStr]))  #  type: ignore


@pytest.mark.parametrize("ptype, ttype", params)
def test_ptype_from_ttype(ptype: type[PType], ttype: type[TType]):
    assert ptype_from_ttype(ttype) == ptype


@pytest.mark.parametrize("ptype, ttype", params)
def test_ttype_from_ptype(ptype: type[PType], ttype: type[TType]):
    assert ttype_from_ptype(ptype) == ttype


ptypes: list[PType] = [
    True,
    False,
    0,
    1,
    2,
    "0",
    "1",
    "test",
    0.0,
    0.1,
    15.2,
    None,
    ["one", 1],
    [1, 2, 3],
    [[[]], 1, ["45", "test"]],
    b"these are some test bytes",
]


@pytest.mark.parametrize("ptype", ptypes)
def test_bytes_roundtrip(ptype: PType):
    bs = bytes_from_ptype(ptype)
    new_type = ptype_from_bytes(bs, ptype.__class__)
    assert ptype == new_type
