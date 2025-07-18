"""Code generated from builtins namespace. Please do not edit."""

from typing import NamedTuple, Sequence, TypeVar, Generic
from tierkreis.controller.data.models import TKR
from tierkreis.controller.data.types import PType

A = TypeVar("A", bound=PType)
T = TypeVar("T", bound=PType)
U = TypeVar("U", bound=PType)
V = TypeVar("V", bound=PType)


class Unzipped(NamedTuple, Generic[U, V]):
    a: TKR[Sequence[U]]  # noqa: F821 # fmt: skip
    b: TKR[Sequence[V]]  # noqa: F821 # fmt: skip


class Untupled(NamedTuple, Generic[U, V]):
    a: TKR[U]  # noqa: F821 # fmt: skip
    b: TKR[V]  # noqa: F821 # fmt: skip


class Headed(NamedTuple, Generic[T]):
    head: TKR[T]  # noqa: F821 # fmt: skip
    rest: TKR[Sequence[T]]  # noqa: F821 # fmt: skip


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
    v: TKR[Sequence[T]]  # noqa: F821 # fmt: skip
    a: TKR[T]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[Sequence[T]]]:  # noqa: F821 # fmt: skip
        return TKR[Sequence[T]]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "builtins"


class head(NamedTuple, Generic[T]):
    v: TKR[Sequence[T]]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[Headed[T]]:  # noqa: F821 # fmt: skip
        return Headed[T]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "builtins"


class impl_len(NamedTuple, Generic[A]):
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


class zip_impl(NamedTuple, Generic[U, V]):
    a: TKR[Sequence[U]]  # noqa: F821 # fmt: skip
    b: TKR[Sequence[V]]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[Sequence[tuple[U, V]]]]:  # noqa: F821 # fmt: skip
        return TKR[Sequence[tuple[U, V]]]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "builtins"


class unzip(NamedTuple, Generic[U, V]):
    value: TKR[Sequence[tuple[U, V]]]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[Unzipped[U, V]]:  # noqa: F821 # fmt: skip
        return Unzipped[U, V]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "builtins"


class tuple_impl(NamedTuple, Generic[U, V]):
    a: TKR[U]  # noqa: F821 # fmt: skip
    b: TKR[V]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[tuple[U, V]]]:  # noqa: F821 # fmt: skip
        return TKR[tuple[U, V]]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "builtins"


class untuple(NamedTuple, Generic[U, V]):
    value: TKR[tuple[U, V]]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[Untupled[U, V]]:  # noqa: F821 # fmt: skip
        return Untupled[U, V]  # noqa: F821 # fmt: skip

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
