from logging import getLogger
from pathlib import Path
from random import randint
import statistics
from sys import argv
from time import sleep
from typing import NamedTuple, Sequence

from tierkreis.controller.data.location import WorkerCallArgs
from tierkreis.controller.data.models import portmapping
from tierkreis.controller.data.types import PType, bytes_from_ptype, ptype_from_bytes
from tierkreis.worker.worker import TierkreisWorkerError
from tierkreis.worker.storage.protocol import WorkerStorage
from tierkreis import Worker


logger = getLogger(__name__)

worker = Worker("builtins")


@worker.task()
def iadd(a: int, b: int) -> int:
    logger.debug(f"iadd {a} {b}")
    return a + b


@worker.task()
def itimes(a: int, b: int) -> int:
    logger.debug(f"itimes {a} {b}")
    return a * b


@worker.task()
def igt(a: int, b: int) -> bool:
    logger.debug(f"igt {a} {b}")
    return a > b


@worker.task()
def neg(a: bool) -> bool:
    return not a


@worker.task()
def impl_and(a: bool, b: bool) -> bool:
    logger.debug(f"and {a} {b}")
    return a and b


@worker.task()
def impl_id[T: PType](value: T) -> T:
    logger.debug(f"id {value}")
    return value


@worker.task()
def append[T](v: list[T], a: T) -> list[T]:  # noqa: E741
    v.append(a)
    return v


@portmapping
class Headed[T: PType](NamedTuple):
    head: T
    rest: list[T]


@worker.task()
def head[T: PType](v: list[T]) -> Headed[T]:  # noqa: E741
    head, rest = v[0], v[1:]
    return Headed(head=head, rest=rest)


@worker.task()
def impl_len[A](v: list[A]) -> int:
    logger.info("len: %s", v)
    return len(v)


@worker.task()
def str_eq(a: str, b: str) -> bool:
    return a == b


@worker.task()
def str_neq(a: str, b: str) -> bool:
    return a != b


@worker.primitive_task()
def fold_values(args: WorkerCallArgs, storage: WorkerStorage) -> None:
    values_glob = storage.glob(str(args.inputs["values_glob"]))
    values_glob.sort(key=lambda x: int(Path(x).name.split("-")[-1]))
    bs = [storage.read_input(Path(value)) for value in values_glob]
    values = [ptype_from_bytes(b) for b in bs]
    storage.write_output(Path(args.outputs["value"]), bytes_from_ptype(values))


@worker.primitive_task()
def unfold_values(args: WorkerCallArgs, storage: WorkerStorage) -> None:
    value_list = ptype_from_bytes(storage.read_input(args.inputs["value"]))
    match value_list:
        case list() | Sequence():
            for i, v in enumerate(value_list):
                storage.write_output(args.output_dir / str(i), bytes_from_ptype(v))
        case _:
            raise TierkreisWorkerError(f"Expected list found {value_list}")


@worker.task()
def concat(lhs: str, rhs: str) -> str:
    return lhs + rhs


@worker.task()
def zip_impl[U, V](a: list[U], b: list[V]) -> list[tuple[U, V]]:
    return list(zip(a, b))


@portmapping
class Unzipped[U: PType, V: PType](NamedTuple):
    a: list[U]
    b: list[V]


@worker.task()
def unzip[U: PType, V: PType](value: list[tuple[U, V]]) -> Unzipped[U, V]:
    value_a, value_b = map(list, zip(*value))
    return Unzipped(a=value_a, b=value_b)


@worker.task()
def tuple_impl[U, V](a: U, b: V) -> tuple[U, V]:
    return (a, b)


@portmapping
class Untupled[U: PType, V: PType](NamedTuple):
    a: U
    b: V


@worker.task()
def untuple[U: PType, V: PType](value: tuple[U, V]) -> Untupled[U, V]:
    logger.info("untuple: %s", value)
    value_a, value_b = value
    return Untupled(a=value_a, b=value_b)


@worker.task()
def mean(values: list[float]) -> float:
    return statistics.mean(values)


@worker.task()
def mod(a: int, b: int) -> int:
    return a % b


@worker.task()
def rand_int(a: int, b: int) -> int:
    return randint(a, b)


@worker.task()
def tkr_sleep(delay_seconds: float) -> bool:
    sleep(delay_seconds)
    return True


if __name__ == "__main__":
    worker.app(argv)
