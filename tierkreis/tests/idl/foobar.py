from typing import NamedTuple
from tierkreis.controller.data.models import portmapping
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
