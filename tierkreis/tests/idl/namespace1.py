from typing import NamedTuple
from tierkreis.controller.data.models import portmapping
from tierkreis import Worker
from tierkreis.controller.data.types import PType

worker = Worker("TestNamespace")


@portmapping
class A(NamedTuple):
    name: dict[str, str]
    age: int


class B(NamedTuple):
    name: dict[str, str]
    age: int


class C[T: PType](NamedTuple):
    a: list[int]
    b: B
    t: T


@worker.task()
def foo(a: int, b: str) -> A: ...
@worker.task()
def bar() -> B: ...
@worker.task()
def z[T: PType](c: C[T]) -> C[T]: ...


expected_namespace = worker.namespace
