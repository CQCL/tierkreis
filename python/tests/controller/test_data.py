from tierkreis.controller.data.graph_data import (
    Const,
    Func,
    GraphData,
    Input,
    Loop,
    Output,
)
from tierkreis.core import Labels


def g() -> GraphData:
    g = GraphData()
    a = g.add(Input("value"))(Labels.VALUE)
    one = g.add(Const(1))(Labels.VALUE)
    N = g.add(Const(10))(Labels.VALUE)

    a_plus = g.add(Func("numerical-worker.iadd", {"a": a, "b": one}))(Labels.VALUE)
    tag = g.add(Func("numerical-worker.igt", {"a": N, "b": a_plus}))(Labels.VALUE)
    g.add(Output({"value": a_plus, "should_continue": tag}))
    return g


def k() -> GraphData:
    t = GraphData()
    six = t.add(Const(6))(Labels.VALUE)
    g_const = t.add(Const(g()))(Labels.VALUE)
    l = t.add(Loop(g_const, {"value": six, "body": g_const}, "value", "tag"))
    t.add(Output({"a": l(Labels.VALUE)}))
    return t


def test_k_graph():
    graph = k()
    print(graph)
    assert False
