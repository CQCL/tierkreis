from collections.abc import Awaitable, Callable

import pytest
from tierkreis._tierkreis import (
    Runtime,
    WaitUntil,
    new_default,
    new_in_memory,
    new_sqlite_memory,
)

from tierkreis.builder import Graph
from tierkreis.builtins import iadd
from tierkreis.controller.data.models import TKR
from tierkreis.controller.data.types import Workflow

runtime_fns = [new_default, new_in_memory, new_sqlite_memory]
runtime_fn_ids = ["default", "in_memory", "sqlite_memory"]


def diamond_graph() -> Workflow[TKR[int], TKR[int]]:
    g = Graph(TKR[int], TKR[int])
    left = g.task(iadd(g.inputs, g.const(1)), has_breakpoint=True)
    right = g.task(iadd(g.inputs, g.const(2)))
    joined = g.task(iadd(left, right), has_breakpoint=True)
    return g.finish_with_outputs(joined)


@pytest.mark.asyncio
@pytest.mark.parametrize("runtime_fn", runtime_fns, ids=runtime_fn_ids)
@pytest.mark.parametrize("enabled", [False, True], ids=["disabled", "enabled"])
async def test_breakpoints(
    runtime_fn: Callable[[], Awaitable[Runtime]], enabled: bool
) -> None:
    graph = diamond_graph()
    locs = {"left": "N2", "right": "N4", "joined": "N5"}
    runtime = await runtime_fn()
    with runtime:
        workflow_id = await runtime.save_workflow("breakpoints", graph)
        if enabled:
            run_id = await runtime.start_new_run(
                workflow_id, {"value": 3}, enable_breakpoints=True
            )
            breakpoints = await runtime.wait_for(
                run_id, condition=WaitUntil.Breakpoint, timeout=10
            )
            assert breakpoints == [locs["left"]]
            breakpoints = await runtime.wait_for(
                run_id, condition=WaitUntil.Blocked, timeout=10
            )
            assert breakpoints == [locs["left"]]
            assert await runtime.paused_nodes(run_id) == [locs["left"]]
            states = await runtime.debug_read_node_states(
                run_id, 0, [locs["left"], locs["right"]]
            )
            assert states[locs["left"]].status == "Paused"
            assert states[locs["right"]].status == "Complete"
            assert (await runtime.get_summary(run_id)).complete_time is None
            with pytest.raises(ValueError, match="not resumable|not hit a breakpoint"):
                await runtime.resume_breakpoints(run_id, [locs["left"], "N999"])
            assert await runtime.paused_nodes(run_id) == [locs["left"]]
            assert await runtime.resume_breakpoints(run_id, []) == []
            assert await runtime.resume_breakpoints(run_id, [locs["left"]]) == [
                locs["left"]
            ]
            breakpoints = await runtime.wait_for(
                run_id, condition=WaitUntil.Breakpoint, timeout=10
            )
            assert breakpoints == [locs["joined"]]
            states = await runtime.debug_read_node_states(run_id, 0, [locs["left"]])
            assert await runtime.resume_breakpoints(run_id) == [locs["joined"]]
        else:
            run_id = await runtime.start_new_run(workflow_id, {"value": 3})
        breakpoints = await runtime.wait_for(
            run_id, condition=WaitUntil.Blocked, timeout=10
        )
        assert breakpoints == []
        assert await runtime.wait_for(run_id, timeout=10) == []
        assert await runtime.get_outputs(run_id) == 9
        assert await runtime.paused_nodes(run_id) == []


def nested_breakpoints() -> Workflow[TKR[list[int]], TKR[list[int]]]:
    inner = Graph(TKR[int], TKR[int])
    inner_task = inner.task(iadd(inner.inputs, inner.const(1)), has_breakpoint=True)
    body = inner.finish_with_outputs(inner_task)
    outer = Graph(TKR[list[int]], TKR[list[int]])
    mapped = outer.map(body, outer.inputs, has_breakpoint=True)
    return outer.finish_with_outputs(mapped)


@pytest.mark.asyncio
@pytest.mark.parametrize("runtime_fn", runtime_fns, ids=runtime_fn_ids)
async def test_nested_breakpoints(
    runtime_fn: Callable[[], Awaitable[Runtime]],
) -> None:
    graph = nested_breakpoints()
    locs = {"M0": "N3.M0.N2", "M1": "N3.M1.N2", "M2": "N3.M2.N2"}
    runtime = await runtime_fn()
    with runtime:
        workflow_id = await runtime.save_workflow("map_breakpoints", graph)
        run_id = await runtime.start_new_run(
            workflow_id, {"value": [0, 1, 2]}, enable_breakpoints=True
        )
        breakpoints = await runtime.wait_for(
            run_id, condition=WaitUntil.Breakpoint, timeout=10
        )
        assert breakpoints == ["N3"]
        await runtime.resume_breakpoints(run_id, ["N3"])
        # Using WaitUntil.Breakpoint here is undefined behavior since we can hit any of the inner breakpoints in any order
        breakpoints = await runtime.wait_for(
            run_id, condition=WaitUntil.Blocked, timeout=10
        )
        assert breakpoints == [locs["M0"], locs["M1"], locs["M2"]]
        await runtime.resume_breakpoints(run_id, [locs["M0"]])
        breakpoints = await runtime.wait_for(
            run_id, condition=WaitUntil.Blocked, timeout=10
        )
        assert breakpoints == [locs["M1"], locs["M2"]]
        states = await runtime.debug_read_node_states(
            run_id, 0, [locs["M0"], locs["M1"], locs["M2"]]
        )
        assert states[locs["M0"]].status == "Complete"
        assert states[locs["M1"]].status == "Paused"
        assert states[locs["M2"]].status == "Paused"
        assert await runtime.paused_nodes(run_id) == [locs["M1"], locs["M2"]]
        await runtime.resume_breakpoints(run_id)
        breakpoints = await runtime.wait_for(
            run_id, condition=WaitUntil.Blocked, timeout=10
        )
        assert breakpoints == []
        assert await runtime.get_outputs(run_id) == [1, 2, 3]


@pytest.mark.asyncio
@pytest.mark.parametrize("runtime_fn", runtime_fns, ids=runtime_fn_ids)
async def test_nested_breakpoints_unpaused(
    runtime_fn: Callable[[], Awaitable[Runtime]],
) -> None:
    graph = nested_breakpoints()
    locs = {"M0": "N3.M0.N2", "M1": "N3.M1.N2", "M2": "N3.M2.N2"}
    runtime = await runtime_fn()
    with runtime:
        workflow_id = await runtime.save_workflow("map_breakpoints_alt", graph)
        run_id = await runtime.start_new_run(
            workflow_id, {"value": [0, 1, 2]}, enable_breakpoints=True
        )
        breakpoints = await runtime.wait_for(
            run_id, condition=WaitUntil.Breakpoint, timeout=10
        )
        assert breakpoints == ["N3"]
        await runtime.resume_breakpoints(run_id, ["N3"])
        # Using WaitUntil.Breakpoint here is undefined behavior since we can hit any of the inner breakpoints in any order
        breakpoints = await runtime.wait_for(
            run_id, condition=WaitUntil.Blocked, timeout=10
        )
        assert breakpoints == [locs["M0"], locs["M1"], locs["M2"]]
        await runtime.resume_breakpoints(run_id, [locs["M0"]])
        breakpoints = await runtime.wait_for(
            run_id, condition=WaitUntil.Breakpoint, timeout=10
        )
        assert breakpoints == [locs["M1"], locs["M2"]]
        states = await runtime.debug_read_node_states(
            run_id, 0, [locs["M0"], locs["M1"], locs["M2"]]
        )
        assert states[locs["M0"]].status != "Paused"
        assert states[locs["M1"]].status == "Paused"
        assert states[locs["M2"]].status == "Paused"
        assert await runtime.paused_nodes(run_id) == [locs["M1"], locs["M2"]]
        await runtime.resume_breakpoints(run_id)
        breakpoints = await runtime.wait_for(
            run_id, condition=WaitUntil.Blocked, timeout=10
        )
        assert breakpoints == []
        assert await runtime.get_outputs(run_id) == [1, 2, 3]
