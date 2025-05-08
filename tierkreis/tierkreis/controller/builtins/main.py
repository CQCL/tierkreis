from logging import getLogger
from pathlib import Path
from sys import argv
from typing import Iterable, Iterator

from tierkreis.value import Value
from tierkreis.worker import Worker


logger = getLogger(__name__)

worker = Worker()


@worker.function()
def iadd(*, a: int, b: int) -> Value[int]:
    logger.debug(f"iadd {a} {b}")
    return Value(value=a + b)


@worker.function()
def itimes(*, a: int, b: int) -> Value[int]:
    logger.debug(f"itimes {a} {b}")
    return Value(value=a * b)


@worker.function()
def igt(*, a: int, b: int) -> Value[bool]:
    logger.debug(f"igt {a} {b}")
    return Value(value=a > b)


@worker.function(name="and")
def impl_and(*, a: bool, b: bool) -> Value[bool]:
    logger.debug(f"igt {a} {b}")
    return Value(value=a and b)


@worker.function(name="id")
def impl_id(*, value: object) -> Value[object]:
    logger.debug(f"id {value}")
    return Value(value=value)


@worker.function()
def append(*, l: list, a: object) -> Value[list]:
    l.append(a)
    return Value(value=l)


@worker.function(name="len")
def impl_len(*, l: list) -> Value[int]:
    return Value(value=len(l))


@worker.function()
def str_eq(*, a: str, b: str) -> Value[bool]:
    return Value(value=a == b)


@worker.function()
def str_neq(*, a: str, b: str) -> Value[bool]:
    return Value(value=a != b)


@worker.function(input_glob=True)
def fold_values(values_glob: Iterable[tuple[str, object]]) -> Value[list]:
    values = [value[1] for value in values_glob]
    return Value(value=values)


@worker.function(output_glob=True)
def unfold_values(*, value: list) -> Iterator[tuple[str, object]]:
    for i, value in enumerate(value):
        yield str(i), value


@worker.function(input_glob=True)
def fold_dict(values_glob: Iterable[tuple[str, object]]) -> Value[list]:
    values = {k: v for k, v in values_glob}
    return Value(value=values)


@worker.function(output_glob=True)
def unfold_dict(*, value: dict[str, object]) -> Iterator[tuple[str, object]]:
    for k, v in value.items():
        yield k, v


@worker.function()
def concat(*, lhs: str, rhs: str) -> Value[str]:
    return Value(value=lhs + rhs)


if __name__ == "__main__":
    worker_definition_path = argv[1]
    worker.run(Path(worker_definition_path))
