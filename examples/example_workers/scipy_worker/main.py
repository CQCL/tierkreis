from sys import argv
from typing import NamedTuple
import numpy as np

from tierkreis.worker.worker import Worker

worker = Worker("scipy_worker")


class PointedArray(NamedTuple):
    a: np.ndarray
    p: int


@worker.task()
def add_point(a: np.ndarray, p: int) -> PointedArray:
    return PointedArray(a, p)


@worker.task()
def eval_point(pa: PointedArray) -> float:
    return pa.a.item(pa.p)


@worker.task()
def linspace(start: float, stop: float, num: int = 50) -> np.ndarray:
    return np.linspace(start, stop, num=num)


@worker.task()
def transpose(a: np.ndarray) -> np.ndarray:
    return a.transpose()


@worker.task()
def reshape(a: np.ndarray, shape: int | list[int]) -> np.ndarray:
    return np.reshape(a, shape)


if __name__ == "__main__":
    worker.app(argv)
