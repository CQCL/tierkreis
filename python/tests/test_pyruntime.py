from typing import Iterable

import pytest

from guppylang.decorator import guppy
from guppylang.module import GuppyModule

from hugr import Hugr, val
from hugr.ext import ExtensionRegistry
from hugr.package import Package
from hugr.std.int import IntVal

from tierkreis.pyruntime import PyRuntime


@pytest.mark.asyncio
async def test_factorial():
    with open("/Users/alanlawrence/factorial_hugr.json") as f:
        h = Hugr.load_json(f.read())
    outs = await PyRuntime().run_graph(h)
    assert outs == [IntVal(120, 5).to_value()]


@pytest.mark.asyncio
async def test_fibonacci():
    with open("/Users/alanlawrence/fibonacci_hugr.json") as f:
        h = Hugr.load_json(f.read())
    outs = await PyRuntime().run_graph(h)
    assert outs == [IntVal(8, 5).to_value()]


@pytest.mark.asyncio
async def test_double_type_change():
    module = GuppyModule("module")

    @guppy(module)
    def foo(b: bool) -> int:
        y = 4
        (y := 1) if (y := b) else (y := 6)
        return y

    (h,) = foo.compile().package.modules
    outs = await PyRuntime().run_graph(h, True)
    assert outs == [IntVal(1, width=6)]
    outs = await PyRuntime().run_graph(h, False)
    assert outs == [IntVal(6, width=6)]


@pytest.mark.asyncio
async def test_break_different_types1a():
    module = GuppyModule("module")

    @guppy(module)
    def foo(x: int) -> int:
        z = 0
        while True:
            if x > 5:
                z = False
                break
            else:
                z = 8
            x += z
        return 3 if z else x

    (h,) = foo.compile().package.modules
    outs = await PyRuntime().run_graph(h, IntVal(3, 6))
    assert outs == [IntVal(11, width=6).to_value()]
    outs = await PyRuntime().run_graph(h, IntVal(6, 6))
    assert outs == [IntVal(6, width=6)]


@pytest.mark.asyncio
async def test_calls_tuples():
    module = GuppyModule("module")

    @guppy(module)
    def foo(x: int) -> tuple[int]:
        return (x,)

    @guppy(module)
    def main(x: int) -> int:
        (y,) = foo(x)
        return y

    h = module.compile().module
    outs = await PyRuntime().run_graph(h, IntVal(3, 6))
    assert outs == [IntVal(3, 6)]
