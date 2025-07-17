"""Code generated from builtins namespace. Please do not edit."""

from typing import NamedTuple, TypeVar, Generic
from tierkreis.controller.data.models import TKR
from tierkreis.controller.data.types import PType

U = TypeVar("U", bound=PType)
V = TypeVar("V", bound=PType)
T = TypeVar("T", bound=PType)
A = TypeVar("A", bound=PType)


class Untupled(NamedTuple, Generic[V, U]):
    b: TKR[V]  # noqa: F821 # fmt: skip
    a: TKR[U]  # noqa: F821 # fmt: skip


class Headed(NamedTuple, Generic[T]):
    rest: TKR[list[T]]  # noqa: F821 # fmt: skip
    head: TKR[T]  # noqa: F821 # fmt: skip


class Unzipped(NamedTuple, Generic[V, U]):
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


class impl_and(NamedTuple):
    a: TKR[bool]  # noqa: F821 # fmt: skip
    b: TKR[bool]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[bool]]:  # noqa: F821 # fmt: skip
        return TKR[bool]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "builtins"


class impl_id(NamedTuple, Generic[T]):
    value: TKR[T]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[T]]:  # noqa: F821 # fmt: skip
        return TKR[T]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "builtins"


class append(NamedTuple, Generic[T]):
    v: TKR[list[T]]  # noqa: F821 # fmt: skip
    a: TKR[T]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[list[T]]]:  # noqa: F821 # fmt: skip
        return TKR[list[T]]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "builtins"


class head(NamedTuple, Generic[T]):
    v: TKR[list[T]]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[Headed[T]]:  # noqa: F821 # fmt: skip
        return Headed[T]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "builtins"


class impl_len(NamedTuple, Generic[A]):
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


class zip_impl(NamedTuple, Generic[V, U]):
    a: TKR[list[U]]  # noqa: F821 # fmt: skip
    b: TKR[list[V]]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[list[tuple[U, V]]]]:  # noqa: F821 # fmt: skip
        return TKR[list[tuple[U, V]]]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "builtins"


class unzip(NamedTuple, Generic[V, U]):
    value: TKR[list[tuple[U, V]]]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[Unzipped[U, V]]:  # noqa: F821 # fmt: skip
        return Unzipped[U, V]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "builtins"


class tuple_impl(NamedTuple, Generic[V, U]):
    a: TKR[U]  # noqa: F821 # fmt: skip
    b: TKR[V]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[tuple[U, V]]]:  # noqa: F821 # fmt: skip
        return TKR[tuple[U, V]]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "builtins"


class untuple(NamedTuple, Generic[V, U]):
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
