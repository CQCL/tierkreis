from types import NoneType
from typing import Sequence
import pytest
from tierkreis.codegen import format_ptype
from tierkreis.controller.data.types import PType

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
