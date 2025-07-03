from types import NoneType, UnionType
from typing import TypeVar, Union
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
    TType,
    bytes_from_ptype,
    ptype_from_bytes,
    ptype_from_ttype,
    ttype_from_ptype,
)


params: list[tuple[type[PType] | UnionType, type[TType] | UnionType]] = [
    (bool, TBool),
    (int, TInt),
    (str, TStr),
    (float, TFloat),
    (NoneType, TNone),
    (bytes, TBytes),
    (list[str], TList[TStr]),
    (list[list[list[NoneType]]], TList[TList[TList[TNone]]]),
    (list[str | list[int]], TList[TStr | TList[TInt]]),
    (list[str | list[int | float]], TList[TStr | TList[TInt | TFloat]]),
    (int | None, TInt | TNone),
    (int | bytes, TInt | TBytes),
]


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
