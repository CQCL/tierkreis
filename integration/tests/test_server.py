import base64

import pytest
from sample_graph import sample_graph as sample_g  # type: ignore
from tierkreis import TierkreisGraph
from tierkreis.builder import ValueSource
from tierkreis.client import ServerRuntime
from tierkreis.core import Labels
from tierkreis.core.function import FunctionName
from tierkreis.core.protos.tierkreis.v1alpha1.controller import NodeId
from tierkreis.core.tierkreis_graph import (
    BoxNode,
    ConstNode,
    FunctionNode,
    GraphValue,
)
from tierkreis.core.type_errors import TierkreisTypeErrors
from tierkreis.core.values import (
    IntValue,
    TierkreisValue,
    VariantValue,
)
from tierkreis.pyruntime import PyRuntime, python_builtin

from . import REASON, release_tests


@pytest.mark.asyncio
async def test_mistyped_op(server_client: ServerRuntime):
    tk_g = TierkreisGraph()
    nod = tk_g.add_func("python_nodes::mistyped_op", inp=tk_g.input["testinp"])
    tk_g.set_outputs(out=nod)
    with pytest.raises(
        RuntimeError,
        match=r"Internal Server Error",
    ):
        await server_client.run_graph(tk_g, testinp=3)


@pytest.mark.asyncio
async def test_infer_errors_when_running(server_client: ServerRuntime) -> None:
    # build graph with two type errors
    tg = TierkreisGraph()
    node_0 = tg.add_const(0)
    node_1 = tg.add_const(1)
    tg.add_edge(node_0["value"], tg.input["illegal"])
    tg.set_outputs(out=node_1["invalid"])

    with pytest.raises(TierkreisTypeErrors) as err:
        await server_client.run_graph(tg)

    assert len(err.value) == 2


def id_graph() -> TierkreisGraph:
    tg = TierkreisGraph()
    tg.set_outputs(value=tg.add_func("python_nodes::id_py", value=tg.input["value"]))
    return tg


@pytest.mark.asyncio
@pytest.mark.skipif(release_tests, reason=REASON)
async def test_runtime_worker(
    server_client: ServerRuntime, local_runtime_launcher
) -> None:
    bar = local_runtime_launcher(
        port=9091,
        worker_uris=[("inner", "http://" + server_client.socket_address())],
        # make sure it has to talk to the other server for the test worker functions
    )
    async with bar as runtime_server:
        await runtime_server.run_graph(id_graph(), value=1)


@pytest.mark.asyncio
async def test_callback(server_client: ServerRuntime):
    tg = TierkreisGraph()
    idnode = tg.add_func("python_nodes::id_with_callback", value=tg.add_const(2))
    tg.set_outputs(out=idnode)

    assert (await server_client.run_graph(tg))["out"].try_autopython() == 2


@pytest.mark.asyncio
async def test_do_callback(server_client: ServerRuntime):
    tk_g = TierkreisGraph()
    tk_g.set_outputs(value=tk_g.input["value"])

    tk_g2 = TierkreisGraph()
    callbacknode = tk_g2.add_func(
        "python_nodes::do_callback",
        graph=tk_g2.input["in_graph"],
        value=tk_g2.input["in_value"],
    )
    tk_g2.set_outputs(out=callbacknode["value"])
    out = await server_client.run_graph(tk_g2, in_value=3, in_graph=tk_g)
    assert out["out"].try_autopython() == 3


@pytest.mark.asyncio
async def test_reports_error(server_client: ServerRuntime):
    pow_g = TierkreisGraph()
    pow_g.set_outputs(
        value=pow_g.add_tag(
            Labels.BREAK,
            value=pow_g.add_func("ipow", a=pow_g.add_const(2), b=pow_g.input["value"]),
        )
    )
    loop_g = TierkreisGraph()
    loop_g.set_outputs(
        value=loop_g.add_func(
            "loop", body=loop_g.add_const(pow_g), value=loop_g.input["value"]
        )
    )

    # Sanity check the graph does execute ipow
    out = await server_client.run_graph(loop_g, value=0)
    assert out == {"value": IntValue(1)}
    expected_err_msg = "Input b to ipow must be positive integer"
    with pytest.raises(RuntimeError, match=expected_err_msg):
        await server_client.run_graph(loop_g, value=-1)


@pytest.fixture
def sample_graph():
    return sample_g()


@pytest.mark.asyncio
async def test_run_graph(
    server_client: ServerRuntime, sample_graph: TierkreisGraph, pyruntime: PyRuntime
):
    ins = {"inp": "hello", "vv": VariantValue("one", TierkreisValue.from_python(1))}
    out_py = await pyruntime.run_graph(
        sample_graph,
        **ins,
    )

    out_rs = await server_client.run_graph(sample_graph, **ins)
    assert out_rs == out_py


@pytest.mark.asyncio
async def test_builtin_signature(server_client: ServerRuntime):
    # TODO test all the implementations as well!
    remote_ns = (await server_client.get_signature()).root.functions
    assert remote_ns.keys() == python_builtin.namespace.functions.keys()
    for f, tkfunc in python_builtin.namespace.functions.items():
        remote_func = remote_ns[f]
        assert remote_func == tkfunc.declaration


@pytest.mark.asyncio
async def test_stack_trace(server_client: ServerRuntime, pyruntime: PyRuntime):
    from tierkreis.builder import (
        Break,
        Const,
        Continue,
        Else,
        If,
        IfElse,
        MakeTuple,
        Namespace,
        Output,
        UnpackTuple,
        graph,
        loop,
    )

    bi = Namespace(await server_client.get_signature())

    @graph()
    def loop_graph(
        value: ValueSource,
    ) -> Output:
        @loop()
        def loop_def(ins_and_outs):
            labels, traces = UnpackTuple(ins_and_outs, 2)
            rest, label = bi.pop(labels)
            rest1, rest2 = bi.copy(rest)
            ntraces = bi.push(traces, bi["python_nodes"].dump_stack(label))
            with IfElse(bi.eq(rest1, Const([]))) as test:
                with If():
                    Break(ntraces)
                with Else():
                    Continue(MakeTuple(rest2, ntraces))
            return Output(test.nref)

        return Output(loop_def(value))

    @graph()
    def outer_graph(
        value: ValueSource,
    ) -> Output:
        return Output(loop_graph(MakeTuple(value, Const([]))))

    (box_node,) = [
        n for n in range(outer_graph.n_nodes) if isinstance(outer_graph[n], BoxNode)
    ]

    (loop_node,) = [
        n
        for n in range(loop_graph.n_nodes)
        if isinstance(nod := loop_graph[n], FunctionNode)
        and nod.function_name == FunctionName("loop")
    ]
    (stack_trace_node,) = [
        inner_idx
        for n in loop_graph.nodes()
        if isinstance(n, ConstNode) and isinstance(n.value, GraphValue)
        for inner_idx in range(n.value.value.n_nodes)
        if isinstance(inner_node := n.value.value[inner_idx], FunctionNode)
        and inner_node.function_name == FunctionName.parse("python_nodes::dump_stack")
    ]
    server_results = await server_client.run_graph(
        outer_graph, value=["foo", "bar", "baz"]
    )

    def loop_iter_id(iter: int) -> NodeId:
        nid = NodeId()
        nid.node_index = stack_trace_node
        nid.prefix = [f"N{box_node}", f"N{loop_node}", f"L{iter}"]
        return nid

    stack_traces = [
        base64.b64encode(bytes(loop_iter_id(iter))).decode("ascii")
        for iter in [1, 2, 3]
    ]
    printed_traces = [
        f"{label} {trace}" for label, trace in zip(["baz", "bar", "foo"], stack_traces)
    ]
    assert server_results["value"].try_autopython() == printed_traces

    pyresults = await pyruntime.run_graph(outer_graph, value=["foo", "bar", "baz"])
    # stack traces are not provided by the python Runtime
    assert pyresults["value"].try_autopython() == ["baz ", "bar ", "foo "]
