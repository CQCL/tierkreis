import pytest

from tierkreis.pyruntime import PyRuntime

from hugr import Hugr
from hugr.val import TRUE, FALSE, Tuple
from hugr.std.int import IntVal


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
