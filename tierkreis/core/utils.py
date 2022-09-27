"""Simple utilities useful throughout the codebase."""
from typing import Callable, Mapping, TypeVar

K = TypeVar("K")
V = TypeVar("V")
W = TypeVar("W")


def map_vals(inp: Mapping[K, V], f: Callable[[V], W]) -> dict[K, W]:
    return {k: f(v) for k, v in inp.items()}
