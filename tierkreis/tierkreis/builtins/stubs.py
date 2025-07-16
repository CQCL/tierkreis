"""Code generated from builtins namespace. Please do not edit."""

from typing import NamedTuple, Sequence
from tierkreis.controller.data.models import TKR, OpaqueType
from tierkreis.controller.data.types import PType


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
    v: TKR[Sequence[T]]  # noqa: F821 # fmt: skip
    a: TKR[T]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[Sequence[T]]]:  # noqa: F821 # fmt: skip
        return TKR[Sequence[T]]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "builtins"


class head[T: PType](NamedTuple):
    v: TKR[Sequence[T]]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[OpaqueType["__main__.Headed[TypeVar]"]]]:  # noqa: F821 # fmt: skip
        return TKR[OpaqueType["__main__.Headed[TypeVar]"]]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "builtins"


class impl_len[A: PType](NamedTuple):
    v: TKR[Sequence[A]]  # noqa: F821 # fmt: skip

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
    a: TKR[Sequence[U]]  # noqa: F821 # fmt: skip
    b: TKR[Sequence[V]]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[Sequence[tuple[U, V]]]]:  # noqa: F821 # fmt: skip
        return TKR[Sequence[tuple[U, V]]]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "builtins"


class unzip[U: PType, V: PType](NamedTuple):
    value: TKR[Sequence[tuple[U, V]]]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[OpaqueType["__main__.Unzipped[TypeVar, TypeVar]"]]]:  # noqa: F821 # fmt: skip
        return TKR[OpaqueType["__main__.Unzipped[TypeVar, TypeVar]"]]  # noqa: F821 # fmt: skip

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


class Untupled[U: PType, V: PType](NamedTuple):
    b: TKR[V]  # noqa: F821 # fmt: skip
    a: TKR[U]  # noqa: F821 # fmt: skip


class untuple[U: PType, V: PType](NamedTuple):
    value: TKR[tuple[U, V]]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[Untupled]:  # noqa: F821 # fmt: skip
        return Untupled  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "builtins"


class mean(NamedTuple):
    values: TKR[Sequence[float]]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[float]]:  # noqa: F821 # fmt: skip
        return TKR[float]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "builtins"
