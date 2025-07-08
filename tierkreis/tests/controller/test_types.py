from types import NoneType, UnionType
from typing import Sequence
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
    TKR,
    bytes_from_ptype,
    format_ttype,
    ptype_from_annotation,
    ptype_from_bytes,
    ptype_from_ttype,
    ttype_from_ptype,
)


type_pairs: Sequence[tuple[type[PType] | UnionType, type[TKR] | UnionType]] = []
type_pairs.append((bool, TBool))
type_pairs.append((int, TInt))
type_pairs.append((str, TStr))
type_pairs.append((float, TFloat))
type_pairs.append((NoneType, TNone))
type_pairs.append((bytes, TBytes))
type_pairs.append((Sequence[str], TList[TStr]))  #  type: ignore
type_pairs.append(
    (
        Sequence[Sequence[Sequence[NoneType]]],
        TList[TList[TList[TNone]]],
    )  #  type: ignore
)
type_pairs.append(
    (Sequence[str | Sequence[int]], TList[TStr | TList[TInt]])
)  #  type: ignore
type_pairs.append(
    (
        Sequence[str | Sequence[int | float]],
        TList[TStr | TList[TInt | TFloat]],
    )  #  type: ignore
)
type_pairs.append((int | None, TInt | TNone))
type_pairs.append((int | bytes, TInt | TBytes))
type_pairs.append((tuple[int, str], TTuple[TInt, TStr]))  #  type: ignore
type_pairs.append((tuple[int | str], TTuple[TInt | TStr]))  #  type: ignore


@pytest.mark.parametrize("ptype, ttype", type_pairs)
def test_ptype_from_ttype(ptype: type[PType], ttype: type[TKR]):
    assert ptype_from_ttype(ttype) == ptype


@pytest.mark.parametrize("ptype, ttype", type_pairs)
def test_ttype_from_ptype(ptype: type[PType], ttype: type[TKR]):
    assert ttype_from_ptype(ptype) == ttype


ptypes: Sequence[PType] = [
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


@pytest.mark.parametrize("ptype, ttype", type_pairs)
def test_ptype_from_annotation(ptype: type[PType], ttype: type[TKR]):
    assert ptype_from_annotation(ptype) == ptype


formats = [
    (TBool, "TBool"),
    (TInt, "TInt"),
    (TFloat, "TFloat"),
    (TStr, "TStr"),
    (TBytes, "TBytes"),
    (TNone, "TNone"),
    (TList[TStr], "TList[TStr]"),
    (TList[TStr | TList[TStr | TInt]], "TList[TStr | TList[TStr | TInt]]"),
    (TTuple[TStr], "TTuple[TStr]"),
    (
        TTuple[TStr | TList[TStr | TInt], TNone],
        "TTuple[TStr | TList[TStr | TInt], TNone]",
    ),
]


@pytest.mark.parametrize("ttype,expected", formats)
def test_format_ttype(ttype: type[TKR], expected: str):
    assert format_ttype(ttype) == expected
