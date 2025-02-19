"""Implementation of simple python-only runtime."""

import asyncio
from typing import (
    Any,
    Callable,
    cast,
    Iterable,
    Optional,
    Sequence,
    TypeVar,
)

from hugr import Hugr, Node, InPort, OutPort, ops, tys, val
from hugr.val import Sum, Value
from hugr.std.int import IntVal, INT_T_DEF


class FunctionNotFound(Exception):
    """Function expected but not found."""

    def __init__(self, fname: str) -> None:
        self.function = fname
        super().__init__(f"Function {fname} not found in namespace.")


class _RuntimeState:
    h: Hugr
    edge_vals: dict[OutPort, Value]
    parent: "_RuntimeState | None"

    def __init__(self, h_or_p: "Hugr | _RuntimeState"):
        self.edge_vals = {}
        (self.h, self.parent) = (
            (h_or_p, None) if isinstance(h_or_p, Hugr) else (h_or_p.h, h_or_p)
        )

    def find(self, outp: OutPort) -> Value:
        if (v := self.edge_vals.get(outp)) is not None:
            return v
        if self.parent is None:
            raise RuntimeError(f"Not found: {outp}")
        return self.parent.find(outp)


def make_val(v: Any, ty: tys.Type) -> Value:
    if isinstance(v, Value):
        return v
    if isinstance(v, bool) and ty == tys.Bool:
        return val.TRUE if v else val.FALSE
    if isinstance(v, int):
        assert isinstance(ty, tys.ExtType)
        assert ty.type_def == INT_T_DEF
        (width_arg,) = ty.args
        assert isinstance(width_arg, tys.BoundedNatArg)
        return IntVal(v, width_arg.n).to_value()
    raise RuntimeError("Don't know how to convert python value: {v}")


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

        main = run_g.root
        if isinstance(run_g[main].op, ops.Module):
            funcs = [
                n for n in run_g.children(main) if isinstance(run_g[n].op, ops.FuncDefn)
            ]
            (main,) = (
                funcs
                if len(funcs) == 1
                else (
                    n for n in funcs if cast(ops.FuncDefn, run_g[n].op).f_name == "main"
                )
            )
        op = run_g[main].op
        inputs: tys.TypeRow
        if isinstance(op, ops.DataflowOp):
            inputs = op.outer_signature().input
        else:
            assert isinstance(op, ops.FuncDefn)
            assert op.params == []
            inputs = op.inputs

        return await self._run_container(
            _RuntimeState(run_g),
            main,
            [make_val(p, t) for p, t in zip(py_inputs, inputs, strict=True)],
        )

    async def _run_container(
        self, st: _RuntimeState, parent: Node, inputs: list[Value]
    ) -> list[Value]:
        """parent is a DataflowOp"""
        parent_node = st.h[parent].op
        if isinstance(parent_node, (ops.DFG, ops.FuncDefn)):
            return await self._run_dataflow_subgraph(st, parent, inputs)
        if isinstance(parent_node, ops.CFG):
            pc: Node = st.h.children(parent)[0]
            while True:
                assert isinstance(st.h[pc].op, ops.DataflowBlock)
                (tag, inputs) = unpack_first(
                    *await self._run_dataflow_subgraph(st, pc, inputs)
                )
                (bb,) = st.h.linked_ports(pc[tag])  # Should only be 1
                pc = bb.node
                if isinstance(st.h[pc].op, ops.ExitBlock):
                    return inputs
        if isinstance(parent_node, ops.Conditional):
            (tag, inputs) = unpack_first(*inputs)
            case_node = st.h.children(parent)[tag]
            return await self._run_dataflow_subgraph(st, case_node, inputs)
        if isinstance(parent_node, ops.TailLoop):
            while True:
                (tag, inputs) = unpack_first(
                    *await self._run_dataflow_subgraph(st, parent, inputs)
                )
                if tag == BREAK_TAG:
                    return inputs
        raise RuntimeError("Unknown container type")

    async def _run_dataflow_subgraph(
        self, outer_st: _RuntimeState, parent: Node, inputs: list[Value]
    ) -> list[Value]:
        # assert isinstance(st.h[parent], ops.DfParentOp) # DfParentOp is a Protocal so no can do
        # FuncDefn corresponds to a Call, but inputs are the arguments
        st = _RuntimeState(outer_st)

        async def get_output(src: OutPort, wait: bool) -> Value:
            while wait and (src not in st.edge_vals):
                assert self.num_workers > 1
                await asyncio.sleep(0)
            return st.edge_vals[src]

        async def get_inputs(node: Node, wait: bool = True) -> list[Value]:
            return [
                await get_output(
                    _single(st.h.linked_ports(InPort(node, inp))), wait=wait
                )
                for inp in _node_inputs(st.h[node].op, False)
            ]

        async def run_node(node: Node) -> list[Value]:
            assert st.h[node].parent == parent
            tk_node = st.h[node].op

            # TODO: ops.Custom, ops.ExtOp, ops.RegisteredOp,
            # ops.CallIndirect, ops.LoadFunc

            if isinstance(tk_node, ops.Output):
                return []
            if isinstance(tk_node, ops.Input):
                return inputs

            if isinstance(
                tk_node,
                (ops.Const, ops.FuncDefn, ops.FuncDecl, ops.AliasDefn, ops.AliasDecl),
            ):
                # These are static only, no value outputs
                return []
            if isinstance(tk_node, ops.LoadConst):
                (const_src,) = st.h.linked_ports(InPort(node, 0))
                cst = st.h[const_src.node].op
                assert isinstance(cst, ops.Const)
                return [cst.val]

            inps = await get_inputs(node, wait=True)
            if isinstance(tk_node, (ops.Conditional, ops.CFG, ops.DFG, ops.TailLoop)):
                return await self._run_container(st, node, inps)
            elif isinstance(tk_node, ops.Call):
                (func_tgt,) = st.h.linked_ports(
                    InPort(node, tk_node._function_port_offset())
                )  # TODO Make this non-private?
                return await self._run_dataflow_subgraph(st, func_tgt.node, inps)
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
                assert len(outs) == _num_value_outputs(st.h[node].op)
                for outport_idx, val in enumerate(outs):
                    outp = OutPort(node, outport_idx)
                    self.callback(outp, val)
                    st.edge_vals[outp] = val
                # signal this node is now done
                queue.task_done()

        que: asyncio.Queue[Node] = asyncio.Queue(len(st.h.children(parent)))

        # add all node names to the queue in topsort order
        # if there are fewer workers than nodes, and the queue is populated
        # in a non-topsort order, some worker may just wait forever for it's
        # node's inputs to become available.
        scheduled: set[Node] = set()

        def schedule(n: Node):
            if n in scheduled:
                return
            scheduled.add(n)  # Ok as acyclic
            for inp in _node_inputs(st.h[n].op, True):
                for src in st.h.linked_ports(InPort(n, inp)):
                    if st.h[src.node].parent == parent:
                        schedule(src.node)
                    else:
                        st.edge_vals[src] = outer_st.find(src)
            que.put_nowait(n)

        for n in st.h.children(
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

        out_node = st.h.children(parent)[1]
        # No need to wait here, all nodes finishing executing:
        result = await get_inputs(out_node, wait=False)

        return result


def unpack_first(*vals: Value) -> tuple[int, list[Value]]:
    pred = vals[0]
    assert isinstance(pred, Sum)
    return (pred.tag, pred.vals + list(vals[1:]))


def _node_inputs(op: ops.Op, include_order: bool = False) -> Iterable[int]:
    if include_order:
        yield -1
    if isinstance(op, ops.DataflowOp):
        n = len(op.outer_signature().input)
        yield from range(n)
    elif isinstance(op, ops.Call):
        n = len(op.instantiation.input)
        yield from range(n)
        n += 1  # Skip Function input
    elif isinstance(op, (ops.Const, ops.FuncDefn)):
        n = 0
    else:
        raise RuntimeError(f"Unknown dataflow op {op}")
    if include_order:
        yield n


def _num_value_outputs(op: ops.Op) -> int:
    if isinstance(op, ops.DataflowOp):
        sig = op.outer_signature()
    elif isinstance(op, ops.Call):
        sig = op.instantiation
    elif isinstance(op, (ops.Const, ops.FuncDefn)):
        return 0
    else:
        raise RuntimeError(f"Unknown dataflow op {op}")
    return len(sig.output)


T = TypeVar("T")


def _single(vals: Iterable[T]) -> T:
    (val,) = vals
    return val


BREAK_TAG = ops.Break(tys.Either([tys.Unit], [tys.Unit])).tag


def run_ext_op(op: ops.Custom, inputs: list[Value]) -> list[Value]:
    def two_ints_logwidth() -> tuple[int, int, int]:
        (a, b) = inputs
        if not isinstance(a, val.Extension):
            a = cast(val.ExtensionValue, a).to_value()
        av = a.val["value"]
        assert isinstance(av, int)

        if not isinstance(b, val.Extension):
            b = cast(val.ExtensionValue, b).to_value()
        bv = b.val["value"]
        assert isinstance(bv, int)

        lw = a.val["log_width"]
        assert isinstance(lw, int)
        assert lw == b.val["log_width"]
        return av, bv, lw

    if op.extension == "arithmetic.int":
        if op.op_name in ["ilt_u", "ilt_s"]:  # TODO how does signedness work here
            (a, b, _) = two_ints_logwidth()
            return [val.TRUE if a < b else val.FALSE]
        if op.op_name in ["igt_u", "igt_s"]:  # TODO how does signedness work here
            (a, b, _) = two_ints_logwidth()
            return [val.TRUE if a > b else val.FALSE]
        if op.op_name == "isub":
            (a, b, lw) = two_ints_logwidth()
            # TODO: wrap/underflow to appropriate width
            return [IntVal(a - b, lw).to_value()]
        if op.op_name == "imul":
            (a, b, lw) = two_ints_logwidth()
            # TODO: wrap/overflow to appropriate width
            return [IntVal(a * b, lw).to_value()]
        if op.op_name == "iadd":
            (a, b, lw) = two_ints_logwidth()
            # TODO: wrap/underflow to appropriate width
            return [IntVal(a + b, lw).to_value()]
    raise RuntimeError(f"Unknown op {op}")
