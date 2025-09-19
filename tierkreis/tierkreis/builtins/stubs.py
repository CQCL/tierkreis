"""Code generated from builtins namespace. Please do not edit."""

from typing import NamedTuple
from tierkreis.controller.data.models import TKR
from tierkreis.controller.data.types import PType


class Headed[T: PType](NamedTuple):
    head: TKR[T]  # noqa: F821 # fmt: skip
    rest: TKR[list[T]]  # noqa: F821 # fmt: skip


class Untupled[U: PType, V: PType](NamedTuple):
    a: TKR[U]  # noqa: F821 # fmt: skip
    b: TKR[V]  # noqa: F821 # fmt: skip


class Unzipped[U: PType, V: PType](NamedTuple):
    a: TKR[list[U]]  # noqa: F821 # fmt: skip
    b: TKR[list[V]]  # noqa: F821 # fmt: skip


class iadd(NamedTuple):
    a: TKR[int]  # noqa: F821 # fmt: skip
    b: TKR[int]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[int]]:  # noqa: F821 # fmt: skip
        return TKR[int]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "builtins"


class itimes(NamedTuple):
    a: TKR[int]  # noqa: F821 # fmt: skip
    b: TKR[int]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[int]]:  # noqa: F821 # fmt: skip
        return TKR[int]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "builtins"


class igt(NamedTuple):
    a: TKR[int]  # noqa: F821 # fmt: skip
    b: TKR[int]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[bool]]:  # noqa: F821 # fmt: skip
        return TKR[bool]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "builtins"


class neg(NamedTuple):
    a: TKR[bool]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[bool]]:  # noqa: F821 # fmt: skip
        return TKR[bool]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "builtins"


class impl_and(NamedTuple):
    a: TKR[bool]  # noqa: F821 # fmt: skip
    b: TKR[bool]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[bool]]:  # noqa: F821 # fmt: skip
        return TKR[bool]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "builtins"


class impl_id[T: PType](NamedTuple):
    value: TKR[T]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[T]]:  # noqa: F821 # fmt: skip
        return TKR[T]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "builtins"


class append[T: PType](NamedTuple):
    v: TKR[list[T]]  # noqa: F821 # fmt: skip
    a: TKR[T]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[list[T]]]:  # noqa: F821 # fmt: skip
        return TKR[list[T]]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "builtins"


class head[T: PType](NamedTuple):
    v: TKR[list[T]]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[Headed[T]]:  # noqa: F821 # fmt: skip
        return Headed[T]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "builtins"


class impl_len[A: PType](NamedTuple):
    v: TKR[list[A]]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[int]]:  # noqa: F821 # fmt: skip
        return TKR[int]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "builtins"


class str_eq(NamedTuple):
    a: TKR[str]  # noqa: F821 # fmt: skip
    b: TKR[str]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[bool]]:  # noqa: F821 # fmt: skip
        return TKR[bool]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "builtins"


class str_neq(NamedTuple):
    a: TKR[str]  # noqa: F821 # fmt: skip
    b: TKR[str]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[bool]]:  # noqa: F821 # fmt: skip
        return TKR[bool]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "builtins"


class concat(NamedTuple):
    lhs: TKR[str]  # noqa: F821 # fmt: skip
    rhs: TKR[str]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[str]]:  # noqa: F821 # fmt: skip
        return TKR[str]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "builtins"


class zip_impl[U: PType, V: PType](NamedTuple):
    a: TKR[list[U]]  # noqa: F821 # fmt: skip
    b: TKR[list[V]]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[list[tuple[U, V]]]]:  # noqa: F821 # fmt: skip
        return TKR[list[tuple[U, V]]]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "builtins"


class unzip[U: PType, V: PType](NamedTuple):
    value: TKR[list[tuple[U, V]]]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[Unzipped[U, V]]:  # noqa: F821 # fmt: skip
        return Unzipped[U, V]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "builtins"


class tuple_impl[U: PType, V: PType](NamedTuple):
    a: TKR[U]  # noqa: F821 # fmt: skip
    b: TKR[V]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[tuple[U, V]]]:  # noqa: F821 # fmt: skip
        return TKR[tuple[U, V]]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "builtins"


class untuple[U: PType, V: PType](NamedTuple):
    value: TKR[tuple[U, V]]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[Untupled[U, V]]:  # noqa: F821 # fmt: skip
        return Untupled[U, V]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "builtins"


class mean(NamedTuple):
    values: TKR[list[float]]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[float]]:  # noqa: F821 # fmt: skip
        return TKR[float]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "builtins"


class mod(NamedTuple):
    a: TKR[int]  # noqa: F821 # fmt: skip
    b: TKR[int]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[int]]:  # noqa: F821 # fmt: skip
        return TKR[int]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "builtins"


class rand_int(NamedTuple):
    a: TKR[int]  # noqa: F821 # fmt: skip
    b: TKR[int]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[int]]:  # noqa: F821 # fmt: skip
        return TKR[int]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "builtins"


class tkr_sleep(NamedTuple):
    delay_seconds: TKR[float]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[bool]]:  # noqa: F821 # fmt: skip
        return TKR[bool]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "builtins"
