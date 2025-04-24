from tierkreis.controller.data.graph import (
    Const,
    Func,
    GraphData,
    Input,
    Loop,
    Map,
    Output,
)
from tierkreis.core import Labels


def loop_body() -> GraphData:
    g = GraphData()
    a = g.add(Input("value"))(Labels.VALUE)
    one = g.add(Const(1))(Labels.VALUE)
    N = g.add(Const(10))(Labels.VALUE)

    a_plus = g.add(Func("numerical-worker.iadd", {"a": a, "b": one}))(Labels.VALUE)
    tag = g.add(Func("numerical-worker.igt", {"a": N, "b": a_plus}))(Labels.VALUE)
    g.add(Output({"value": a_plus, "should_continue": tag}))
    return g


def sample_graphdata() -> GraphData:
    g = GraphData()
    six = g.add(Const(6))(Labels.VALUE)
    g_const = g.add(Const(loop_body()))(Labels.VALUE)
    loop = g.add(
        Loop(g_const, {"value": six, "body": g_const}, "should_continue", Labels.VALUE)
    )
    g.add(Output({"a": loop(Labels.VALUE)}))
    return g


def doubler() -> GraphData:
    g = GraphData()
    value = g.add(Input(Labels.VALUE))(Labels.VALUE)
    two = g.add(Const(2))(Labels.VALUE)
    out = g.add(Func("numerical-worker.itimes", {"a": value, "b": two}))(Labels.VALUE)
    g.add(Output({Labels.VALUE: out}))
    return g


def sample_map() -> GraphData:
    g = GraphData()
    Ns_const = g.add(Const(list(range(21))))(Labels.VALUE)
    Ns = g.add(Func("numerical-worker.unfold_values", {Labels.VALUE: Ns_const}))
    doubler_const = g.add(Const(doubler()))(Labels.VALUE)

    map_def = Map(
        doubler_const,
        Ns(Labels.VALUE)[0],
        Labels.VALUE,
        Labels.VALUE,
        {"doubler": doubler_const},
    )
    m = g.add(map_def)
    folded = g.add(Func("numerical-worker.fold_values", {"values_glob": m("*")}))
    g.add(Output({Labels.VALUE: folded(Labels.VALUE)}))
    return g
