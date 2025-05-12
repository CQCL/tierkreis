from tierkreis import Labels
from tierkreis.controller.data.graph import GraphData, Const, Eval, Func, Output, Input


def doubler_plus() -> GraphData:
    g = GraphData()
    inp = g.add(Input("doubler_input"))("doubler_input")
    intercept = g.add(Input("intercept"))("intercept")
    two = g.add(Const(2))(Labels.VALUE)
    mul = g.add(Func("builtins.itimes", {"a": inp, "b": two}))(Labels.VALUE)
    out = g.add(Func("builtins.iadd", {"a": mul, "b": intercept}))(Labels.VALUE)
    g.add(Output({"doubler_output": out}))
    return g


def simple_eval() -> GraphData:
    g = GraphData()
    zero = g.add(Const(0))(Labels.VALUE)
    six = g.add(Const(6))(Labels.VALUE)
    doubler_const = g.add(Const(doubler_plus()))(Labels.VALUE)
    e = g.add(Eval(doubler_const, {"doubler_input": six, "intercept": zero}))
    g.add(Output({Labels.VALUE: e("doubler_output")}))
    return g
