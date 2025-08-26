from pathlib import Path
import pytest
from tierkreis.codegen import format_namespace
from tierkreis.exceptions import TierkreisError
from tierkreis.idl.models import GenericType
from tierkreis.namespace import Namespace
from tierkreis.idl.type_symbols import type_symbol
import tests.idl.namespace1

type_symbols = [
    ("uint8", GenericType(int, [])),
    ("string", GenericType(str, [])),
    ("Array<integer>", GenericType(list, [GenericType(int, [])])),
    (
        "Record<Array<string>>",
        GenericType(
            dict, [GenericType(str, []), GenericType(list, [GenericType(str, [])])]
        ),
    ),
    (
        "Record<Array<C<T, A>>>",
        GenericType(
            dict,
            [
                GenericType(str, []),
                GenericType(list, [GenericType("C", ["T", "A"])]),
            ],
        ),
    ),
]
type_symbols_for_failure = ["decimal", "unknown", "duration"]
dir = Path(__file__).parent
typespecs = [(dir / "namespace1.tsp", tests.idl.namespace1.expected_namespace)]


@pytest.mark.parametrize("type_symb,expected", type_symbols)
def test_type_t(type_symb: str, expected: type):
    assert (expected, "") == type_symbol(type_symb)


@pytest.mark.parametrize("path,expected", typespecs)
def test_namespace(path: Path, expected: Namespace):
    namespace = Namespace.from_spec_file(path)
    assert format_namespace(namespace) == format_namespace(expected)


@pytest.mark.parametrize("type_symb", type_symbols_for_failure)
def test_parser_fail(type_symb: str):
    with pytest.raises(TierkreisError):
        type_symbol(type_symb)
