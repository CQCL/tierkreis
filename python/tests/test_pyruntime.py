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
