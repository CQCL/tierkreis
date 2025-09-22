"""Code generated from TestNamespace namespace. Please do not edit."""

from typing import Literal, NamedTuple, Sequence, TypeVar, Generic, Protocol, Union
from types import NoneType
from tierkreis.controller.data.models import TKR, OpaqueType
from tierkreis.controller.data.types import PType, Struct


class A(NamedTuple):
    age: TKR[int]  # noqa: F821 # fmt: skip
    name: TKR[dict[str, str]]  # noqa: F821 # fmt: skip



class B(Struct, Protocol):
    age: int  # noqa: F821 # fmt: skip
    name: dict[str, str]  # noqa: F821 # fmt: skip



class C[T: PType](NamedTuple):
    a: TKR[list[int]]  # noqa: F821 # fmt: skip
    b: TKR[B]  # noqa: F821 # fmt: skip
    t: TKR[T]  # noqa: F821 # fmt: skip


class foo(NamedTuple):
    a: TKR[int]  # noqa: F821 # fmt: skip
    b: TKR[str]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[A]: # noqa: F821 # fmt: skip
        return A # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "TestNamespace" 

class bar(NamedTuple):
    

    @staticmethod
    def out() -> type[TKR[B]]: # noqa: F821 # fmt: skip
        return TKR[B] # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "TestNamespace" 

class z[T: PType](NamedTuple):
    b: TKR[B]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[C[T]]: # noqa: F821 # fmt: skip
        return C[T] # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "TestNamespace" 
    