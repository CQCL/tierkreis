from types import NoneType, UnionType
from typing import Sequence
import pytest
from tierkreis.controller.data.types import (
    PType,
    bytes_from_ptype,
    format_ptype,
    is_ptype,
    ptype_from_bytes,
)


type_list: Sequence[type[PType] | UnionType] = []
type_list.append(bool)
type_list.append(int)
type_list.append(str)
type_list.append(float)
type_list.append(NoneType)
type_list.append(bytes)
type_list.append(Sequence[str])
type_list.append(Sequence[Sequence[Sequence[NoneType]]])
type_list.append(Sequence[str | Sequence[int]])
type_list.append(Sequence[str | Sequence[int | float]])
type_list.append(int | None)
type_list.append(int | bytes)
type_list.append(tuple[int, str])
type_list.append(tuple[int | str])

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
    new_type = ptype_from_bytes(bs)
    assert ptype == new_type


@pytest.mark.parametrize("ptype", type_list)
def test_ptype_from_annotation(ptype: type[PType]):
    assert is_ptype(ptype)


formats: list[tuple[type[PType], str]] = [
    (bool, "bool"),
    (int, "int"),
    (float, "float"),
    (str, "str"),
    (bytes, "bytes"),
    (NoneType, "NoneType"),
    (Sequence[str], "Sequence[str]"),
    (Sequence[str | Sequence[str | int]], "Sequence[str | Sequence[str | int]]"),
    (tuple[str], "tuple[str]"),
    (
        tuple[str | Sequence[str | int], NoneType],
        "tuple[str | Sequence[str | int], NoneType]",
    ),
]


@pytest.mark.parametrize("ttype,expected", formats)
def test_format_ttype(ttype: type[PType], expected: str):
    assert format_ptype(ttype) == expected
