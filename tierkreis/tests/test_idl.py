from typing import NamedTuple
import pytest
from tierkreis.codegen import format_namespace
from tierkreis.controller.data.models import portmapping
from tierkreis.namespace import FunctionSpec, Namespace
from tierkreis.idl.combinators import type_t, spec


@portmapping
class A(NamedTuple):
    name: dict[str, str]
    age: int


class B(NamedTuple):
    name: dict[str, str]
    age: int


@portmapping
class C(NamedTuple):
    a: list[int]


expected_namespace = Namespace("TestNamespace", functions={})
expected_namespace._add_function_spec(
    FunctionSpec("foo", "TestNamespace", {"a": int, "b": str}, [], A)
)
expected_namespace._add_function_spec(
    FunctionSpec("bar", "TestNamespace", {}, [], B),
)
expected_namespace._add_function_spec(
    FunctionSpec("z", "TestNamespace", {"a": C}, [], C),
)
txt = """
portmapping A {
  name: Record<string>;
  age: uint8;
}
struct B {
  name: Record<string>;
  age: uint8;
}
portmapping C {
    a: Array<integer>;
}
interface TestNamespace {
  foo(a: integer, b:string): A;
  bar(): B;
  z(a: C): C;
}
"""


type_symbols = [
    ("uint8", int),
    ("string", str),
    ("Array<integer>", list[int]),
    ("Record<Array<string>>", dict[str, list[str]]),
]


@pytest.mark.parametrize("type_symbol,expected", type_symbols)
def test_type_t(type_symbol: str, expected: type):
    assert (expected, "") == type_t(type_symbol)


def test_namespace():
    namespace = spec(txt)
    assert format_namespace(namespace[0]) == format_namespace(expected_namespace)
