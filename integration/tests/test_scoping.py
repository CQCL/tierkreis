from typing import AsyncIterator

import pytest
from tierkreis.builder import Const, Copyable, Output, Scope, ValueSource, graph
from tierkreis.client import RuntimeClient, ServerRuntime

from . import PYTHON_WORKER

# This avoids errors on every call to a decorated _GraphDef


@pytest.mark.asyncio
async def test_run_scoped_program(bi, client: RuntimeClient) -> None:
    @graph()
    def g() -> Output:
        a = Const(3)
        with Scope():
            b = Copyable(Const(2))
            with Scope():
                c = bi.iadd(a, b)
            d = bi.iadd(c, b)
        e = bi.iadd(d, Const(1))
        return Output(value=e)

    outputs = await client.run_graph(g)
    assert outputs["value"].try_autopython() == 8


@pytest.fixture(scope="session")
async def outer_server_client(
    local_runtime_launcher, server_client
) -> AsyncIterator[ServerRuntime]:
    async with local_runtime_launcher(
        port=9090,
        worker_uris=[("inner", "http://" + server_client.socket_address())],
    ) as outer:
        yield outer


@pytest.mark.asyncio
async def test_remote_scopes(outer_server_client, bi):
    @graph()
    def g() -> Output:
        a = Copyable(Const(3))
        with Scope("inner"):
            b = Const(2)
            c = bi.iadd(b, a)
        d = bi.iadd(a, c)
        return Output(value=d)

    outputs = await outer_server_client.run_graph(g)
    assert outputs["value"].try_autopython() == 8


@pytest.mark.asyncio
async def test_remote_scopes_escape_hatch(local_runtime_launcher, bi):
    # Here the inner runtime does NOT have a python worker, but the outer does
    async with local_runtime_launcher(
        port=8081,
    ) as inner:
        async with local_runtime_launcher(
            port=9091,
            worker_uris=[("inner", "http://" + inner.socket_address())],
            workers=[("python", PYTHON_WORKER)],
        ) as outer:

            @graph()
            def g() -> Output:
                with Scope("inner"):
                    o = bi["python_nodes"].id_py(Const(1))
                return Output(out=o)

            res = await outer.run_graph(g)
            assert res["out"].try_autopython() == 1


@pytest.mark.asyncio
async def test_escape_hatch_preserves_callback(local_runtime_launcher, bi):
    # Here only the outer runtime has a python worker, neither middle/inner
    async with local_runtime_launcher(
        port=8081,
    ) as inner:
        async with local_runtime_launcher(
            port=9081, worker_uris=[("inner", "http://" + inner.socket_address())]
        ) as middle:
            async with local_runtime_launcher(
                port=9091,
                worker_uris=[("middle", "http://" + middle.socket_address())],
                workers=[("python", PYTHON_WORKER)],
            ) as outer:

                @graph()
                def g_middle_only(value: ValueSource) -> Output:
                    with Scope("inner"):
                        b = Const(4)
                        r = bi.iadd(value, b)
                    return Output(value=r)

                res = await middle.run_graph(g_middle_only, value=3)
                assert res["value"].try_autopython() == 7
                with pytest.raises(RuntimeError, match="Could not find location inner"):
                    await outer.run_graph(g_middle_only, value=3)

                # Quick sanity check that we can run middle in that scope
                @graph()
                def run_middle_from_outer() -> Output:
                    with Scope("middle"):
                        r = bi.eval(Const(g_middle_only), value=Const(5))
                    return Output(out=r)

                res = await outer.run_graph(run_middle_from_outer)
                assert res["out"].try_autopython() == 9

                # Now try and run middle in that scope via escape hatch and callback
                @graph()
                def use_escape_hatch(arg: ValueSource) -> Output:
                    with Scope("middle"):
                        # do_callback runs on the python worker, attached to <outer>.
                        # The callback needs to execute the graph *in this Scope*,
                        # i.e. on the middle runtime. (Note: a more complex case would
                        # attach the python worker to a second runtime child of <outer>,
                        # that might be even harder.)
                        r = bi["python_nodes"].do_callback(
                            graph=Const(g_middle_only), value=arg
                        )
                    return Output(outp=r)

                res = await outer.run_graph(use_escape_hatch, arg=7)
                assert res["outp"].try_autopython() == 11


@pytest.mark.asyncio
async def test_double_remote_scopes_escape_hatch(local_runtime_launcher, bi):
    async with local_runtime_launcher(port=8081) as inner:
        async with local_runtime_launcher(
            port=9092,
            worker_uris=[("inner", "http://" + inner.socket_address())],
        ) as middle:
            async with local_runtime_launcher(
                port=9093,
                worker_uris=[("middle", "http://" + middle.socket_address())],
                workers=[("python", PYTHON_WORKER)],
            ) as outer:

                @graph()
                def g2() -> Output:
                    with Scope("middle"):
                        with Scope("inner"):
                            o = bi["python_nodes"].id_py(Const(2))
                    return Output(out=o)

                res = await outer.run_graph(g2)
                assert res["out"].try_autopython() == 2


# TODO we now need some test that the stuff in the scope
# is actually running remotely.


@pytest.mark.asyncio
async def test_worker_scopes(server_client: ServerRuntime, bi):
    @graph()
    def g() -> Output:
        with Scope("python"):
            x = bi["python_nodes"].id_py(Const(1))
        return Output(value=x)

    outputs = await server_client.run_graph(g)
    assert outputs["value"].try_autopython() == 1


@pytest.mark.asyncio
async def test_double_scope(server_client: ServerRuntime, bi, local_runtime_launcher):
    async with local_runtime_launcher(
        port=8081,
        worker_uris=[("inner", "http://" + server_client.socket_address())],
    ) as inner:
        async with local_runtime_launcher(
            port=9091,
            worker_uris=[("inner", "http://" + inner.socket_address())],
        ) as outer:

            @graph()
            def g() -> Output:
                with Scope("inner/inner"):
                    with Scope("python"):
                        x = bi["python_nodes"].id_py(Const(1))
                return Output(value=x)

            outputs = await outer.run_graph(g)
            assert outputs["value"].try_autopython() == 1


@pytest.mark.asyncio
async def test_nested_callback(outer_server_client: ServerRuntime, bi):
    @graph()
    def g_only_on_outer(value: ValueSource) -> Output:
        # Only the outer runtime has a scope called "Inner"
        with Scope("inner"):
            a = bi["python_nodes"].id_py(value)
        return Output(value=a)

    @graph()
    def g_that_calls_back(in_graph: ValueSource, in_value: ValueSource) -> Output:
        # do_callback must run on the python worker attached to the inner
        # runtime, but when it runs it's in_graph argument,
        # that must callback all the way to the *outer* runtime.
        a = bi["python_nodes"].do_callback(graph=in_graph, value=in_value)
        return Output(out=a)

    out = await outer_server_client.run_graph(
        g_that_calls_back, in_value=3, in_graph=g_only_on_outer
    )
    assert out["out"].try_autopython() == 3


@pytest.mark.asyncio
async def test_callback_inside_scope(outer_server_client: ServerRuntime, bi):
    @graph()
    def g_only_on_outer(value: ValueSource) -> Output:
        # This graph will only run on the outer runtime,
        # because only that has a subscope called "Inner"
        with Scope("inner"):
            a = bi["python_nodes"].id_py(value)
        return Output(value=a)

    @graph()
    def g_anywhere(value: ValueSource):  # This will run anywhere
        a = bi["python_nodes"].id_py(value)
        return Output(value=a)

    @graph()
    def g_that_calls_back(in_graph: ValueSource, in_value: ValueSource) -> Output:
        with Scope("inner"):
            # do_callback should only call back to this *inner* runtime
            a = bi["python_nodes"].do_callback(graph=in_graph, value=in_value)
        return Output(out=a)

    # Sanity check that the graphs are valid
    out = await outer_server_client.run_graph(g_only_on_outer, value=3)
    assert out["value"].try_autopython() == 3
    out = await outer_server_client.run_graph(g_anywhere, value=4)
    assert out["value"].try_autopython() == 4
    out = await outer_server_client.run_graph(
        g_that_calls_back, in_graph=g_anywhere, in_value=5
    )
    assert out["out"].try_autopython() == 5
    expected_err_regex = (
        r"failed to run function in worker\n"
        # The next is from the run_graph callback made by the worker
        r".*Run_graph execution failed with message:"
        # And this is the error from inside the graph run by the callback
        r".*Could not find location inner to run box"
    )
    with pytest.raises(RuntimeError, match=expected_err_regex):
        out = await outer_server_client.run_graph(
            g_that_calls_back, in_graph=g_only_on_outer, in_value=6
        )
        # Graph ran -> callback went all the way back to outer scope
        pytest.fail("Graph ran, so callback escaped user's explicit scope")
