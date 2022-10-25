#!/usr/bin/env python
import asyncio
from dataclasses import dataclass
from typing import Generic, Optional, TypeVar, cast

from tierkreis import TierkreisGraph
from tierkreis.client.server_client import RuntimeClient, with_runtime_client
from tierkreis.core.python import RuntimeGraph
from tierkreis.core.tierkreis_struct import TierkreisStruct
from tierkreis.core.types import StarKind
from tierkreis.worker import CallbackHook, Namespace
from tierkreis.worker.prelude import start_worker_server

root = Namespace()
namespace = root["python_nodes"]
subspace = namespace["subspace"]
callback = CallbackHook()

A = TypeVar("A")


@namespace.function(type_vars={A: StarKind()})  # type: ignore
async def id_py(value: A) -> A:
    "Identity function which passes on the value on port 'value'."
    return value


@namespace.function()
async def increment(value: int) -> int:
    return value + 1


@subspace.function(name="increment")
async def increment_subspace(value: int) -> int:
    # Intentionally give a different definition in the subspace
    # to check names are being resolved correctly
    return value + 2


# This deliberately has the wrong python type annotation because
# the TierkreisFunction's types are copied from there. Thus, this
# produces a TierkreisFunction which claims to be of type Int->Int,
# even though it actually produces floats.
@namespace.function()
async def mistyped_op(inp: int) -> int:
    return inp + 1.1  # type: ignore


@namespace.function()
async def python_add(a: int, b: int) -> int:
    return a + b


@dataclass
class IdDelayInputs(TierkreisStruct, Generic[A]):
    wait: int
    value: A


@dataclass
class IdDelayOutputs(TierkreisStruct, Generic[A]):
    value: A


@namespace.function(
    type_vars={A: StarKind()},  # type: ignore
)
async def id_delay(inputs: IdDelayInputs[A]) -> IdDelayOutputs[A]:
    await asyncio.sleep(inputs.wait)
    return IdDelayOutputs(value=inputs.value)


@dataclass
class FailOutput(TierkreisStruct):
    pass


@namespace.function()
async def fail() -> FailOutput:
    raise RuntimeError("fail node was run")


@namespace.function()
async def test_option(x: Optional[int]) -> int:
    if x is None:
        return -1
    # Just check the runtime values correspond with the type annotations
    assert isinstance(x, int)
    return x


@namespace.function(type_vars={cast(TypeVar, A): StarKind()})
@with_runtime_client(callback)
async def id_with_callback(client: RuntimeClient, value: A) -> A:
    """Callback to runtime via channel to run identity"""

    tg = TierkreisGraph()
    tg.set_outputs(out=tg.input["inp"])

    # async with channel as channel:
    #     rc = RuntimeClient(channel)
    outs = await client.run_graph(tg, inp=value)

    return cast(A, outs["out"])


@dataclass
class GraphInOut(TierkreisStruct, Generic[A]):
    value: A


@namespace.function(type_vars={cast(TypeVar, A): StarKind()})
@with_runtime_client(callback)
async def do_callback(
    client: RuntimeClient, graph: RuntimeGraph[GraphInOut, GraphInOut], value: A
) -> A:
    """Callback to runtime via channel to run graph provided"""
    g = graph.graph

    outs = await client.run_graph(g, value=value)

    return cast(A, outs["value"])


if __name__ == "__main__":
    start_worker_server("test_worker", root, callback)
