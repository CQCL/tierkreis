#!/usr/bin/env python
import random
from typing import TypeVar

import numpy as np

from tierkreis.worker import Namespace
from tierkreis.worker.prelude import start_worker_server

root = Namespace()
namespace = root["sc22"]

A = TypeVar("A")

CandRecord = tuple[list[float], float]

# @dataclass(frozen=True)
# class CandRecord(TierkreisStruct):
#     params: list[float]
#     score: float

random.seed(4)


@namespace.function()
async def new_params(
    prev_params: list[CandRecord],
) -> list[float]:
    assert len(prev_params) > 0
    if len(prev_params) == 1:
        return [random.random()] * len(prev_params[0])

    first, second = prev_params[-2:]

    ar1 = np.array(first[0])
    ar2 = np.array(second[0])

    diff = ar2 - ar1
    diff[diff == 0.0] = 1e-14
    grad = (second[1] - first[1]) / diff
    ar2 -= 0.1 * grad
    return list(ar2)


@namespace.function()
async def converged(prev: list[CandRecord]) -> bool:
    n = 5
    if len(prev) >= n:
        last_n = np.array([x[1] for x in prev[-n:]])
        moving_av = sum((last_n - last_n.mean()) ** 2)
        return bool(moving_av < 1e-5)

    return False


if __name__ == "__main__":
    start_worker_server("sc22_worker", root)
