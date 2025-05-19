from tierkreis.controller.data.graph import (
    Const,
    Eval,
    Func,
    GraphData,
    Input,
    Output,
)
from tierkreis import Labels


def ternary_add() -> GraphData:
    g = GraphData()
    a = g.add(Input("a"))("a")
    b = g.add(Input("b"))("b")
    c = g.add(Input("c"))("c")

    step_one = g.add(Func("builtins.iadd", {"a": a, "b": b}))(Labels.VALUE)
    step_two = g.add(Func("builtins.iadd", {"a": step_one, "b": c}))(Labels.VALUE)

    g.add(Output({"ternary_add_output": step_two}))
    return g


def double_partial() -> GraphData:
    g = GraphData()
    one = g.add(Const(1))(Labels.VALUE)
    two = g.add(Const(2))(Labels.VALUE)
    three = g.add(Const(3))(Labels.VALUE)
    termary_add_const = g.add(Const(ternary_add()))(Labels.VALUE)

    add_add_1 = g.add(Eval(termary_add_const, {"a": one}))("body")
    add_3 = g.add(Eval(add_add_1, {"b": two}))("body")
    six = g.add(Eval(add_3, {"c": three}))("ternary_add_output")

    g.add(Output({"double_partial_output": six}))
    return g
