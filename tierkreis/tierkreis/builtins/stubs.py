"""Code generated from builtins namespace. Please do not edit."""

from dataclasses import dataclass
from typing import Literal, NamedTuple
from tierkreis.controller.data.core import NodeIndex, PortID
from tierkreis.controller.data.graph import Function
from tierkreis.controller.data.refs import (
    IntRef,
    StrRef,
    FloatRef,
    DictConvertibleRef,
)


class iadd(NamedTuple):
    a: int
    b: int

    @staticmethod
    def out(idx: NodeIndex) -> int:
        return IntRef.from_value_ref(idx, "value")

    @property
    def namespace(self) -> str:
        return "builtins"


class CiaddOutput(NamedTuple):
    a: int
    value: DictConvertibleRef[Literal["CIAddOutInner"]]

    @staticmethod
    def from_value_ref(n: NodeIndex, p: PortID) -> "CiaddOutput":
        return CiaddOutput(
            a=IntRef.from_value_ref(n, "a"),
            value=DictConvertibleRef[Literal["CIAddOutInner"]].from_value_ref(
                n, "value"
            ),
        )


class ciadd(NamedTuple):
    a: int
    b: int

    @staticmethod
    def out(idx: NodeIndex) -> CiaddOutput:
        return CiaddOutput.from_value_ref(idx, "value")

    @property
    def namespace(self) -> str:
        return "builtins"


class itimes(NamedTuple):
    a: int
    b: int

    @staticmethod
    def out(idx: NodeIndex) -> int:
        return IntRef.from_value_ref(idx, "value")

    @property
    def namespace(self) -> str:
        return "builtins"


class concat(NamedTuple):
    lhs: str
    rhs: str

    @staticmethod
    def out(idx: NodeIndex) -> str:
        return StrRef.from_value_ref(idx, "value")

    @property
    def namespace(self) -> str:
        return "builtins"


class mean(NamedTuple):
    values: DictConvertibleRef[Literal["list"]]

    @staticmethod
    def out(idx: NodeIndex) -> float:
        return FloatRef.from_value_ref(idx, "value")

    @property
    def namespace(self) -> str:
        return "builtins"
