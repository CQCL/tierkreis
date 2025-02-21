import pytest
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from hugr import Hugr, tys, val
from hugr.build import Cfg
from hugr.std.int import INT_T, DivMod, IntVal

from tierkreis.pyruntime import PyRuntime


@pytest.mark.asyncio
async def test_factorial():
    with open("factorial_hugr.json") as f:
        h = Hugr.load_json(f.read())
    outs = await PyRuntime().run_graph(h)
    assert outs == [IntVal(120, 5)]


@pytest.mark.asyncio
async def test_fibonacci():
    with open("fibonacci_hugr.json") as f:
        h = Hugr.load_json(f.read())
    outs = await PyRuntime().run_graph(h)
    assert outs == [IntVal(8, 5)]

@pytest.mark.asyncio
async def test_xor_and_cfg():
    with open("xor_and_cfg.json") as f:
        h = Hugr.load_json(f.read())
    for a in [False, True]:
        for b in [False, True]:
            outs = await PyRuntime().run_graph(h, a, b)
            assert outs == [val.TRUE if a ^ b else val.FALSE, val.TRUE if a and b else val.FALSE]

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
    outs = await PyRuntime().run_graph(h, 3)
    assert outs == [IntVal(11, width=6)]
    outs = await PyRuntime().run_graph(h, 6)
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


@pytest.mark.asyncio
async def test_exec_array():
    from guppylang.std.builtins import array

    module = GuppyModule("test")

    @guppy(module)
    def main() -> int:
        a = array(1, 2, 3)
        return a[0] + a[1] + a[2]

    h = module.compile().module
    outs = await PyRuntime().run_graph(h)
    assert outs == [IntVal(6, 6)]


@pytest.mark.asyncio
async def test_subscript_assign():
    from guppylang.std.builtins import array, owned

    module = GuppyModule("test")

    @guppy(module)
    def foo(xs: array[int, 3] @ owned, idx: int, n: int) -> array[int, 3]:
        xs[idx] = n
        return xs

    @guppy(module)
    def main() -> int:
        xs = array(0, 0, 0)
        xs = foo(xs, 0, 2)
        return xs[0]

    h = module.compile().module
    outs = await PyRuntime().run_graph(h)
    assert outs == [IntVal(2, 6)]


@pytest.mark.asyncio
async def test_dom_edges():
    c = Cfg(tys.Bool, INT_T)

    entry = c.add_entry()
    cst = entry.load(IntVal(6))
    entry.set_block_outputs(*entry.inputs())  # Use Bool to branch, so INT_T

    middle_1 = c.add_successor(entry[0])
    dm = middle_1.add(DivMod(*middle_1.inputs(), cst))
    middle_1.set_single_succ_outputs(dm[0])

    middle_2 = c.add_successor(entry[1])
    middle_2.set_single_succ_outputs(*middle_2.inputs())

    merge = c.add_successor(middle_1)
    c.branch(middle_2[0], merge)
    merge.set_single_succ_outputs(*merge.inputs(), cst)

    c.branch_exit(merge)

    outs = await PyRuntime().run_graph(c.hugr, val.TRUE, 12)
    assert outs == [IntVal(12), IntVal(6)]

    outs = await PyRuntime().run_graph(c.hugr, val.FALSE, 18)
    assert outs == [IntVal(3), IntVal(6)]
