from typing import NamedTuple
from tierkreis.controller.data.models import portmapping
from tierkreis import Worker

worker = Worker("TestNamespace")


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
    b: B


@worker.task()
def foo(a: int, b: str) -> A: ...
@worker.task()
def bar() -> B: ...
@worker.task()
def z(a: C) -> C: ...


expected_namespace = worker.namespace
