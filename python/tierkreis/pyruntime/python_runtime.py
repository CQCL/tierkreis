"""Implementation of simple python-only runtime."""

import asyncio
from copy import deepcopy
from typing import TYPE_CHECKING, Any, Callable, Iterable, Optional, Tuple, Sequence

from hugr import Hugr, Node, InPort, OutPort, ops, tys, val
from hugr.val import Sum, Value


class FunctionNotFound(Exception):
    """Function expected but not found."""

    def __init__(self, fname: str) -> None:
        self.function = fname
        super().__init__(f"Function {fname} not found in namespace.")


# ALAN can we implement RuntimeClient somehow,
# e.g. type_check -> we support all ops as in Hugr, and can run?
class PyRuntime:
    """A simplified python-only Tierkreis runtime. Can be used with builtin
    operations and python only namespaces that are locally available."""

    def __init__(self, num_workers: int = 1):
        """Initialise with locally available namespaces, and the number of
        workers (asyncio tasks) to use in execution."""
        self.num_workers = num_workers
        self._callback: Optional[Callable[[OutPort, Value], None]] = None

    def set_callback(self, callback: Optional[Callable[[OutPort, Value], None]]):
        """Set a callback function that takes an OutPort and Value,
        which will be called every time a value is output.
        Can be used to inspect intermediate values."""
        self._callback = callback

    def callback(
        self,
        out_port: OutPort,
        val: Value,
    ):
        """If a callback function is set, call it with an edge and the value on
        the edge."""
        if self._callback:
            self._callback(out_port, val)

    async def run_graph(
        self,  # ALAN next line we've changed sig, does ignore work?
        run_g: Hugr,  # type:ignore
        *py_inputs: Any,
    ) -> list[Value]:
        """Run a tierkreis graph using the python runtime, and provided inputs.
        Returns the outputs of the graph.
        """

        def make_val(v: Any) -> Value:  # TODO take desired type also, e.g. int width
            if isinstance(v, Value):
                return v
            raise RuntimeError("Don't know how to convert python value: {v}")

        main = run_g.root
        if isinstance(run_g[main].op, ops.Module):
            (main,) = (
                n
                for n in run_g.children(main)
                for op in [run_g[n].op]
                if isinstance(op, ops.FuncDefn) and op.f_name == "main"
            )
        return await self._run_container(run_g, main, [make_val(p) for p in py_inputs])

    async def _run_container(
        self, run_g: Hugr, parent: Node, inputs: Sequence[Value]
    ) -> list[Value]:
        """parent is a DataflowOp"""
        parent_node = run_g[parent].op
        if isinstance(parent_node, (ops.DFG, ops.FuncDefn)):
            return await self._run_dataflow_subgraph(run_g, parent, inputs)
        if isinstance(parent_node, ops.CFG):
            pc = run_g.children(parent)[0]
            assert isinstance(pc, ops.DataflowBlock)
            while True:
                (tag, inputs) = unpack_first(
                    *await self._run_dataflow_subgraph(run_g, pc, inputs)
                )
                (bb,) = run_g.linked_ports(pc[tag])  # Should only be 1
                pc = bb.node
                if isinstance(pc, ops.ExitBlock):
                    return inputs
        if isinstance(parent_node, ops.Conditional):
            (tag, inputs) = unpack_first(*inputs)
            case_node = run_g.children(parent)[tag]
            return await self._run_dataflow_subgraph(run_g, case_node, inputs)
        if isinstance(parent_node, ops.TailLoop):
            while True:
                (tag, inputs) = unpack_first(
                    *await self._run_dataflow_subgraph(run_g, parent, inputs)
                )
                if tag == ops.Break.tag:
                    return inputs
        raise RuntimeError("Unknown container type")

    async def _run_dataflow_subgraph(
        self, run_g: Hugr, parent: Node, inputs: Sequence[Value]
    ) -> list[Value]:
        # assert isinstance(run_g[parent], ops.DfParentOp) # DfParentOp is a Protocal so no can do
        # FuncDefn corresponds to a Call, but inputs are the arguments
        runtime_state: dict[OutPort, Value] = {}

        async def get_output(src: OutPort, wait: bool) -> Value:
            while wait and (src not in runtime_state):
                assert self.num_workers > 1
                await asyncio.sleep(0)
            return runtime_state[src]

        async def get_inputs(node: Node, wait: bool = True) -> list[Value]:
            return [
                await get_output(outp, wait=wait)
                for (inp, outps) in run_g.incoming_links(node)
                if isinstance(run_g.port_kind(inp), tys.ValueKind)
                for outp in outps  # Should only be one for a ValueKind
            ]

        async def run_node(node: Node) -> list[Value]:
            tk_node = run_g[node].op

            # TODO: ops.Custom, ops.ExtOp, ops.RegisteredOp,
            # ops.CallIndirect, ops.LoadFunc

            if isinstance(tk_node, ops.Output):
                return []
            if isinstance(tk_node, ops.Input):
                return list(inputs)

            if isinstance(
                tk_node,
                (ops.Const, ops.FuncDefn, ops.FuncDecl, ops.AliasDefn, ops.AliasDecl),
            ):
                # These are static only, no value outputs
                return []
            if isinstance(tk_node, ops.LoadConst):
                (const_src,) = run_g.linked_ports(InPort(node, 0))
                cst = run_g[const_src.node].op
                assert isinstance(cst, ops.Const)
                return [cst.val]

            inps = await get_inputs(node, wait=True)
            if isinstance(tk_node, (ops.Conditional, ops.CFG, ops.DFG, ops.TailLoop)):
                return await self._run_container(run_g, node, inputs)
            elif isinstance(tk_node, ops.Call):
                (func_tgt,) = run_g.linked_ports(InPort(node, tk_node._function_port_offset())) # TODO Make this non-private?
                return await self._run_dataflow_subgraph(run_g, func_tgt.node, inps)
            elif isinstance(tk_node, ops.Tag):
                return [Sum(tk_node.tag, tk_node.sum_ty, inps)]
            elif isinstance(tk_node, ops.MakeTuple):
                return [Sum(0, tys.Sum([tk_node.types]), inps)]
            elif isinstance(tk_node, ops.UnpackTuple):
                (sum_val,) = inps
                assert isinstance(sum_val, Sum)
                return sum_val.vals
            elif isinstance(tk_node, ops.Custom):
                return run_ext_op(tk_node, inps)
            elif isinstance(tk_node, ops.AsExtOp):
                return run_ext_op(tk_node.ext_op.to_custom_op(), inps)
            else:
                raise RuntimeError("Unknown node type.")

        async def worker(queue: asyncio.Queue[Node]):
            # each worker gets the next node in the queue
            while True:
                node = await queue.get()
                # If the node is not yet runnable,
                # wait/block until it is, do not try to run any other node
                outs = await run_node(node)

                # assign outputs to edges
                # assert len(outs) == run_g.num_out_ports(node) # No, must exclude ConstKind etc.
                for outport_idx, val in enumerate(outs):
                    outp = OutPort(node, outport_idx)
                    self.callback(outp, val)
                    runtime_state[outp] = val
                # signal this node is now done
                queue.task_done()

        que: asyncio.Queue[Node] = asyncio.Queue(len(run_g.children(parent)))

        # add all node names to the queue in topsort order
        # if there are fewer workers than nodes, and the queue is populated
        # in a non-topsort order, some worker may just wait forever for it's
        # node's inputs to become available.
        scheduled: set[Node] = set()

        def schedule(n: Node):
            if n in scheduled:
                return
            scheduled.add(n)  # Ok as acyclic
            for inp, outps in run_g.incoming_links(n):
                # Exclude non-executed predecessors (const/function edges)
                if isinstance(inp, (tys.ValueKind, tys.OrderKind)):
                    for outp in outps:
                        schedule(outp.node)
            que.put_nowait(n)

        for n in run_g.children(
            parent
        ):  # Input, then Output, then any unreachable from Output
            schedule(n)

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

        out_node = run_g.children(parent)[1]
        return await get_inputs(
            out_node, wait=False
        )  # No need to wait, all nodes finishing executing.


def unpack_first(*vals: Value) -> tuple[int, list[Value]]:
    pred = vals[0]
    assert isinstance(pred, Sum)
    pred.vals.extend(vals[1:])
    return (pred.tag, pred.vals)

def run_ext_op(op: ops.Custom, inputs: list[Value]) -> list[Value]:
    if op.extension == "arithmetic.int":
        if op.op_name == "ilt_u":
            (a,b) = inputs
            assert isinstance(a, val.Extension)
            a = a.val['value']
            assert isinstance(a, int)
            assert isinstance(b, val.Extension)
            b = b.val['value']
            assert isinstance(b, int)
            # TODO need to implement overflow/wrapping according to type(argument)
            return [val.TRUE if a < b else val.FALSE]
    raise RuntimeError(f"Unknown op {op}")
    
