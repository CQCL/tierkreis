from typing import NamedTuple
from tierkreis.codegen import format_namespace
from tierkreis.controller.data.models import portmapping
from tierkreis.idl.parser import typespec_parser, NamespaceTransformer
from tierkreis.namespace import FunctionSpec, Namespace


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


def test_load_transform():
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
    tree = typespec_parser.parse(txt)
    ns = NamespaceTransformer().spec(tree)
    assert format_namespace(ns) == format_namespace(expected_namespace)
