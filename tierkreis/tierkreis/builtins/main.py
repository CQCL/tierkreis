from dataclasses import dataclass
from logging import getLogger
import statistics
from sys import argv
from typing import Any, Iterator, NamedTuple, Sequence

from pydantic import BaseModel

from tierkreis.value import Value
from tierkreis.worker.worker import Worker


logger = getLogger(__name__)

worker = Worker("builtins")


@worker.function()
def iadd(a: int, b: int) -> int:
    logger.debug(f"iadd {a} {b}")
    return a + b


# class CIAddOutInner(NamedTuple):
#     x: int


# class CIAddOut(NamedTuple):
#     a: int
#     value: CIAddOutInner


# @worker.function()
# def ciadd(a: int, b: int) -> CIAddOut:
#     logger.debug(f"ciadd {a} {b}")
#     return CIAddOut(a=a, value=CIAddOutInner(x=a + b))


@worker.function()
def itimes(a: int, b: int) -> int:
    logger.debug(f"itimes {a} {b}")
    return a * b


@worker.function()
def igt(a: int, b: int) -> bool:
    logger.debug(f"igt {a} {b}")
    return a > b


@worker.function(name="and")
def impl_and(a: bool, b: bool) -> bool:
    logger.debug(f"igt {a} {b}")
    return a and b


# @worker.function(name="id")
# def impl_id[T](value: T) -> T:
#     logger.debug(f"id {value}")
#     return value


@worker.function()
def append[T](l: list[T], a: T) -> list[T]:  # noqa: E741
    l.append(a)
    return l


class Headed[T](BaseModel):
    head: T
    rest: list[T]


# @worker.function()
# def head[T](l: list[T]) -> Headed[T]:  # noqa: E741
#     head, rest = l[0], l[1:]
#     return Headed(head=head, rest=rest)


@worker.function(name="len")
def impl_len(l: list) -> int:  # noqa: E741
    logger.info("len: %s", l)
    return len(l)


@worker.function()
def str_eq(a: str, b: str) -> bool:
    return a == b


@worker.function()
def str_neq(a: str, b: str) -> bool:
    return a != b


# @worker.function()
# def fold_values[T](values_glob: Iterator[tuple[str, T]]) -> list[T]:
#     values = [1 for value in values_glob]
#     return values


# @worker.function()
# def unfold_values[T](value: list[T]) -> Iterator[tuple[str, T]]:
#     for i, v in enumerate(value):
#         yield str(i), v


# @worker.function()
# def fold_dict[T](values_glob: Iterator[tuple[str, T]]) -> dictstr, T]]:
#     values = {k: v for k, v in values_glob}
#     return values


# @worker.function()
# def unfold_dict[T](value: dict[str, T]) -> Iterator[tuple[str, T]]:
#     for k, v in value.items():
#         yield k, v


@worker.function()
def concat(lhs: str, rhs: str) -> str:
    return lhs + rhs


# @worker.function(name="zip")
# def zip_impl[U, V](a: list[U], b: list[V]) -> list[tuple[U, V]]]:
#     return list(zip(a, b))


# class Unzipped[U, V](BaseModel):
#     a: list[U]
#     b: list[V]


# @worker.function()
# def unzip[U, V](value: list[tuple[U, V]]) -> Unzipped[U, V]:
#     value_a, value_b = map(list, zip(*value))
#     return Unzipped(a=value_a, b=value_b)


# @worker.function(name="tuple")
# def tuple_impl[U, V](a: U, b: V) -> tuple[U, V]:
#     return (a, b)


# class Untupled[U, V](BaseModel):
#     a: U
#     b: V


# @worker.function()
# def untuple[U, V](value: tuple[U, V]) -> Untupled[U, V]:
#     logger.info("untuple: %s", value)
#     value_a, value_b = value
#     return Untupled(a=value_a, b=value_b)


@worker.function()
def mean(values: list[float]) -> float:
    return statistics.mean(values)


if __name__ == "__main__":
    worker.app(argv)
