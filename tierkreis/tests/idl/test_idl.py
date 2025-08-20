from pathlib import Path
import pytest
from tierkreis.codegen import format_namespace
from tierkreis.namespace import Namespace
from tierkreis.idl.spec import SpecParser
from tierkreis.idl.type_symbols import TypeParser
import tests.idl.namespace1

type_symbols = [
    ("uint8", int),
    ("string", str),
    ("Array<integer>", list[int]),
    ("Record<Array<string>>", dict[str, list[str]]),
]


@pytest.mark.parametrize("type_symb,expected", type_symbols)
def test_type_t(type_symb: str, expected: type):
    assert (expected, "") == TypeParser().type_symbol()(type_symb)


dir = Path(__file__).parent
typespecs = [(dir / "namespace1.tsp", tests.idl.namespace1.expected_namespace)]


@pytest.mark.parametrize("path,expected", typespecs)
def test_namespace(path: Path, expected: Namespace):
    with open(path) as fh:
        namespace = SpecParser().spec()(fh.read())
    assert format_namespace(namespace[0]) == format_namespace(expected)
