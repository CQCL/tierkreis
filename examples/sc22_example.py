import asyncio
import json
import sys
from typing import Optional

from grpclib.client import Channel
from pytket._tket.circuit import Circuit
from sympy import symbols

# from tierkreis.core.graphviz import render_graph, tierkreis_to_graphviz
from tierkreis.builder import (
    Break,
    Const,
    Continue,
    Copyable,
    Else,
    If,
    IfElse,
    MakeTuple,
    Namespace,
    Output,
    ValueSource,
    closure,
    lazy_graph,
    loop,
)
from tierkreis.client.runtime_client import RuntimeClient
from tierkreis.client.server_client import ServerRuntime


def runtime_client_from_args(args: list[str]) -> Optional[RuntimeClient]:
    if len(args) == 0:
        import sc22_worker.main

        import pytket_worker.main  # type: ignore
        from tierkreis.pyruntime import PyRuntime

        return PyRuntime(
            [
                sc22_worker.main.root,
                pytket_worker.main.root,
            ]
        )
    elif len(args) == 1:
        # cl.set_callback(lambda x, y: print(x, y))
        host, port = args[0].split(":")
        c = Channel(host, int(port))
        return ServerRuntime(c)
    else:
        return None


async def run_test(cl: RuntimeClient):
    sig = await cl.get_signature()
    bi = Namespace(sig)
    pt, sc = (bi["pytket"], bi["sc22"])

    a, b = symbols("a b")
    ansatz = Circuit(2)
    ansatz.Rx(0.5 + a, 0).Rx(-0.5 + b, 1).CZ(0, 1).Rx(0.5 + b, 0).Rx(
        -0.5 + a, 1
    ).measure_all()

    @lazy_graph()
    def initial(run: ValueSource) -> Output:
        init_params = Copyable(Const([0.2, 0.2]))
        init_score = bi.eval(run, params=init_params)
        p = MakeTuple(init_params, init_score)
        lst = bi.push(Const([]), p)
        return Output(lst)

    @lazy_graph()
    def load_circuit() -> Output:
        js_str = json.dumps(ansatz.to_dict())
        c = pt.load_circuit_json(Const(js_str))
        return Output(c)

    @lazy_graph()
    def zexp_to_parity(zexp: ValueSource) -> Output:
        y = bi.fsub(Const(1.0), zexp)
        return Output(bi.fdiv(y, Const(2.0)))

    @lazy_graph()
    def main() -> Output:
        circ = load_circuit()

        @closure()
        def run_circuit(params: ValueSource) -> Output:
            syms = Const(["a", "b"])
            # substitute parameters in circuit with values a, b
            subs = pt.substitute_symbols(circ, syms, params)
            res = pt.execute(subs, Const(1000), Const("AerBackend"))
            return Output(zexp_to_parity(pt.z_expectation(res)))

        run_circuit.copyable()

        @loop()
        def loop_def(initial: ValueSource) -> Output:
            recs = Copyable(initial)
            new_cand = Copyable(sc.new_params(recs))
            score = run_circuit(new_cand)
            pair = MakeTuple(new_cand, score)
            recs = Copyable(bi.push(recs, pair))

            with IfElse(sc.converged(recs)) as lbody:
                with If():
                    Break(recs)
                with Else():
                    Continue(recs)
            return Output(lbody.nref)

        init_val = initial(run_circuit)
        return Output(loop_def(init_val))

    # tg
    # display(tg)
    # render_graph(tg, "../../figs/main_graph", "pdf")

    return await cl.run_graph(main.graph)


async def main():
    cl = runtime_client_from_args(sys.argv[1:])
    if cl is None:
        print(f"Usage: {__file__} [<host>:<port>]")
        sys.exit(-1)
    else:
        res = await run_test(cl)
        print(res["value"].viz_str())


if __name__ == "__main__":
    asyncio.run(main())
