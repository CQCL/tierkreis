from pathlib import Path
from typing import NamedTuple
import pytest
from tierkreis.codegen import format_namespace
from tierkreis.controller.data.models import portmapping
from tierkreis.namespace import FunctionSpec, Namespace
from tierkreis.idl.spec import spec
from tierkreis.idl.types import type_symbol
import tests.idl.foobar

type_symbols = [
    ("uint8", int),
    ("string", str),
    ("Array<integer>", list[int]),
    ("Record<Array<string>>", dict[str, list[str]]),
]


@pytest.mark.parametrize("type_symb,expected", type_symbols)
def test_type_t(type_symb: str, expected: type):
    assert (expected, "") == type_symbol(type_symb)


dir = Path(__file__).parent
typespecs = [(dir / "foobar.tsp", tests.idl.foobar.expected_namespace)]


@pytest.mark.parametrize("path,expected", typespecs)
def test_namespace(path: Path, expected: Namespace):
    with open(path) as fh:
        namespace = spec(fh.read())
    assert format_namespace(namespace[0]) == format_namespace(expected)
