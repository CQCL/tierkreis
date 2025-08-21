from types import NoneType
import pytest
from tierkreis.controller.data.types import PType, format_ptype

formats: list[tuple[type[PType], str]] = [
    (bool, "bool"),
    (int, "int"),
    (float, "float"),
    (str, "str"),
    (bytes, "bytes"),
    (NoneType, "NoneType"),
    (list[str], "list[str]"),
    (list[str | list[str | int]], "list[str | list[str | int]]"),
    (tuple[str], "tuple[str]"),
    (
        tuple[str | list[str | int], NoneType],
        "tuple[str | list[str | int], NoneType]",
    ),
]


@pytest.mark.parametrize("ttype,expected", formats)
def test_format_ttype(ttype: type[PType], expected: str):
    assert format_ptype(ttype) == expected
