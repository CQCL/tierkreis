from sys import argv
from typing import Annotated, NamedTuple
import numpy as np

from tierkreis.worker.worker import Worker

worker = Worker("scipy_worker")
NDArray = Annotated[np.ndarray, "custom_deserializer"]


class PointedArray(NamedTuple):
    a: NDArray
    p: int


@worker.task()
def add_point(a: NDArray, p: int) -> PointedArray:
    return PointedArray(a, p)


@worker.task()
def eval_point(pa: PointedArray) -> float:
    return pa.a.item(pa.p)


@worker.task()
def linspace(start: float, stop: float, num: int = 50) -> NDArray:
    return np.linspace(start, stop, num=num)


@worker.task()
def transpose(a: NDArray) -> NDArray:
    return a.transpose()


@worker.task()
def reshape(a: NDArray, shape: int | list[int]) -> NDArray:
    return np.reshape(a, shape)


if __name__ == "__main__":
    worker.app(argv)
