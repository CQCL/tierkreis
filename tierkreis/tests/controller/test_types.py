from dataclasses import dataclass
from types import NoneType, UnionType
from typing import Self, Sequence
from pydantic import BaseModel
import pytest
from tierkreis.controller.data.types import (
    PType,
    bytes_from_ptype,
    is_ptype,
    ptype_from_bytes,
)


class DummyBaseModel(BaseModel):
    a: int
    b: bytes


@dataclass
class DummyDictConvertible:
    a: int

    def to_dict(self) -> dict:
        return {"a": self.a}

    @classmethod
    def from_dict(cls, args: dict) -> "DummyDictConvertible":
        return DummyDictConvertible(a=args["a"])


@dataclass
class DummyListConvertible:
    a: int

    def to_list(self) -> list:
        return list(range(self.a))

    @classmethod
    def from_list(cls, args: list) -> "DummyListConvertible":
        return DummyListConvertible(a=len(args))


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
    [[[]], 1, ["45", "test", b"test bytes"]],
    b"these are some test bytes",
    {"one": 1, "two": "two", "bytes": b"asdf"},
    DummyDictConvertible(a=11),
    DummyListConvertible(a=5),
    DummyBaseModel(a=5, b=b"some bytes"),
]


@pytest.mark.parametrize("ptype", ptypes)
def test_bytes_roundtrip(ptype: PType):
    bs = bytes_from_ptype(ptype)
    new_type = ptype_from_bytes(bs, type(ptype))
    assert ptype == new_type


@pytest.mark.parametrize("ptype", type_list)
def test_ptype_from_annotation(ptype: type[PType]):
    assert is_ptype(ptype)
