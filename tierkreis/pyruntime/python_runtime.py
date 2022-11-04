"""Implementation of simple python-only runtime."""
import asyncio
from copy import deepcopy
from typing import TYPE_CHECKING, Any, Callable, Iterable, Optional, Tuple, cast

import networkx as nx  # type: ignore

from tierkreis.client.runtime_client import RuntimeClient
from tierkreis.core import Labels
from tierkreis.core.function import FunctionName
from tierkreis.core.signature import Signature
from tierkreis.core.tierkreis_graph import (
    BoxNode,
    ConstNode,
    FunctionNode,
    GraphValue,
    IncomingWireType,
    InputNode,
    MatchNode,
    OutputNode,
    TagNode,
    TierkreisEdge,
    TierkreisGraph,
)
from tierkreis.core.type_inference import _TYPE_CHECK, infer_graph_types
from tierkreis.core.utils import map_vals
from tierkreis.core.values import StructValue, TierkreisValue, VariantValue
from tierkreis.pyruntime import python_builtin

if TYPE_CHECKING:
    from tierkreis.core.tierkreis_graph import _EdgeData
    from tierkreis.worker.namespace import Namespace


class _ValueNotFound(Exception):
    def __init__(self, tke: TierkreisEdge) -> None:
        self.edge = tke
        super().__init__(f"Value not found on edge {tke.source} -> {tke.target}")


class OutputNotFound(_ValueNotFound):
    """Node output expected but not found."""


class InputNotFound(_ValueNotFound):
    """Node input expected but not found."""


class FunctionNotFound(Exception):
    """Function expected but not found."""

    def __init__(self, fname: FunctionName) -> None:
        self.function = fname
        super().__init__(f"Function {fname} not found in namespace.")


class PyRuntime(RuntimeClient):
    """A simplified python-only Tierkreis runtime. Can be used with builtin
    operations and python only namespaces that are locally available."""

    def __init__(self, roots: Iterable["Namespace"], num_workers: int = 1):
        """Initialise with locally available namespaces, and the number of
        workers (asyncio tasks) to use in execution."""
        self.root = deepcopy(python_builtin.namespace)
        for root in roots:
            self.root.merge_namespace(root)
        self.num_workers = num_workers
        self.callback: Callable[[TierkreisEdge, TierkreisValue], None]
        self.set_callback(None)

    def set_callback(
        self, callback: Optional[Callable[[TierkreisEdge, TierkreisValue], None]]
    ):
        """Set a callback function that takes a TierkreisEdge and
        TierkreisValue, which will be called every time a edge receives an
        output. Can be used to inspect intermediate values."""
        self.callback = callback if callback is not None else lambda _1, _2: None

    async def run_graph(
        self,
        run_g: TierkreisGraph,
        /,
        **py_inputs: Any,
    ) -> dict[str, TierkreisValue]:
        """Run a tierkreis graph using the python runtime, and provided inputs.
        Returns the outputs of the graph.
        """
        total_nodes = run_g._graph.number_of_nodes()
        runtime_state: dict["_EdgeData", TierkreisValue] = {}

        async def run_node(node: int) -> dict[str, TierkreisValue]:
            tk_node = run_g[node]

            if isinstance(tk_node, OutputNode):
                return {}
            if isinstance(tk_node, InputNode):
                return map_vals(py_inputs, TierkreisValue.from_python)

            if isinstance(tk_node, ConstNode):
                return {Labels.VALUE: tk_node.value}

            in_edges = list(run_g.in_edges(node))
            while not all(e.to_edge_handle() in runtime_state for e in in_edges):
                # wait for inputs to become available
                # only useful if there are other workers that can do things
                # while this one waits
                assert self.num_workers > 1
                await asyncio.sleep(0)
            try:
                in_values = (
                    (e, runtime_state.pop(e.to_edge_handle())) for e in in_edges
                )
            except KeyError as key_e:
                raise InputNotFound(run_g._to_tkedge(key_e.args[0])) from key_e

            inps = {e.target.port: val for e, val in in_values}
            if isinstance(tk_node, FunctionNode):
                fname = tk_node.function_name
                if fname.namespaces == [] and fname.name == "eval":
                    return await self._run_eval(inps)
                elif fname.namespaces == [] and fname.name == "loop":
                    return await self._run_loop(inps)
                else:
                    function = self.root.get_function(fname)
                    if function is None:
                        raise FunctionNotFound(fname)
                    return (await function.run(StructValue(inps))).values

            elif isinstance(tk_node, BoxNode):
                return await self.run_graph(
                    tk_node.graph,
                    **inps,
                )

            elif isinstance(tk_node, MatchNode):
                return self._run_match(inps)

            elif isinstance(tk_node, TagNode):
                return {
                    Labels.VALUE: VariantValue(tk_node.tag_name, inps[Labels.VALUE])
                }

            else:
                raise RuntimeError("Unknown node type.")

        async def worker(queue: asyncio.Queue[int]):
            # each worker gets the next node in the queue
            while True:
                node = await queue.get()
                # If the node is not yet runnable,
                # wait/block until it is, do not try to run any other node
                outs = await run_node(node)

                # assign outputs to edges
                for out_edge in run_g.out_edges(node):
                    try:
                        val = outs.pop(out_edge.source.port)
                    except KeyError as key_e:
                        raise OutputNotFound(out_edge) from key_e
                    tkval = TierkreisValue.from_python(val)
                    self.callback(out_edge, tkval)
                    runtime_state[out_edge.to_edge_handle()] = tkval
                # signal this node is now done
                queue.task_done()

        que: asyncio.Queue[int] = asyncio.Queue(total_nodes)
        for node in nx.topological_sort(run_g._graph):
            # add all node names to the queue in topsort order
            # if there are fewer workers than nodes, and the queue is populated
            # in a non-topsort order, some worker may just wait forever for it's
            # node's inputs to become available.
            que.put_nowait(node)

        workers = [asyncio.create_task(worker(que)) for _ in range(self.num_workers)]
        queue_complete = asyncio.create_task(que.join())

        # wait for either all nodes to complete, or for a worker to return
        await asyncio.wait(
            [queue_complete, *workers], return_when=asyncio.FIRST_COMPLETED
        )
        if not queue_complete.done():
            # If the queue hasn't completed, it means one of the workers has
            # raised - find it and propagate the exception.
            # even if the rest of the graph has not completed
            for t in workers:
                if t.done():
                    t.result()  # this will raise
        for task in workers:
            task.cancel()

        # Wait until all worker tasks are cancelled.
        await asyncio.gather(*workers, return_exceptions=True)

        return {
            e.target.port: runtime_state.pop(e.to_edge_handle())
            for e in run_g.in_edges(run_g.output_node_idx)
        }

    async def _run_eval(
        self, ins: dict[str, TierkreisValue]
    ) -> dict[str, TierkreisValue]:
        thunk = cast(GraphValue, ins.pop(Labels.THUNK)).value
        return await self.run_graph(thunk, **ins)

    async def _run_loop(
        self, ins: dict[str, TierkreisValue]
    ) -> dict[str, TierkreisValue]:
        body = cast(GraphValue, ins.pop("body")).value
        while True:
            outs = await self.run_graph(
                body,
                **ins,
            )
            out = cast(
                VariantValue,
                outs[Labels.VALUE],
            )
            nxt = {"value": out.value}
            if out.tag == Labels.BREAK:
                return nxt
            else:
                ins = nxt

    def _run_match(self, ins: dict[str, TierkreisValue]) -> dict[str, TierkreisValue]:
        variant = cast(VariantValue, ins[Labels.VARIANT_VALUE])
        thunk = cast(GraphValue, ins[variant.tag]).value

        newg = TierkreisGraph()
        boxinps: dict[str, IncomingWireType] = {
            inp: newg.input[inp] for inp in thunk.inputs()
        }
        boxinps[Labels.VALUE] = newg.add_const(variant.value)
        box = newg.add_box(thunk, **boxinps)
        newg.set_outputs(**{out: box[out] for out in thunk.outputs()})
        return {Labels.THUNK: GraphValue(newg)}

    async def get_signature(self) -> Signature:
        return self.root.extract_signature(True)

    async def type_check_graph(self, tg) -> TierkreisGraph:
        return infer_graph_types(tg, await self.get_signature())

    async def type_check_graph_with_inputs(
        self, tg, inputs: StructValue
    ) -> Tuple[TierkreisGraph, StructValue]:
        return infer_graph_types(tg, await self.get_signature(), inputs)

    @property
    def can_type_check(self) -> bool:
        return _TYPE_CHECK
