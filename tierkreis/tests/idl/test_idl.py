from pathlib import Path
import pytest
from tierkreis.codegen import format_namespace
from tierkreis.namespace import Namespace
from tierkreis.idl.spec import spec
from tierkreis.idl.type_symbols import type_symbol
import tests.idl.namespace1

type_symbols = [
    ("uint8", int),
    ("string", str),
    ("Array<integer>", list[int]),
    ("Record<Array<string>>", dict[str, list[str]]),
]
dir = Path(__file__).parent
typespecs = [(dir / "namespace1.tsp", tests.idl.namespace1.expected_namespace)]


@pytest.mark.parametrize("type_symb,expected", type_symbols)
def test_type_t(type_symb: str, expected: type):
    assert (expected, "") == type_symbol(type_symb)


@pytest.mark.parametrize("path,expected", typespecs)
def test_namespace(path: Path, expected: Namespace):
    with open(path) as fh:
        namespace = spec(fh.read())
    assert format_namespace(namespace[0]) == format_namespace(expected)
