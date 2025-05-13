from tierkreis.controller.data.graph import (
    Const,
    Eval,
    Func,
    GraphData,
    IfElse,
    Input,
    Loop,
    Map,
    Output,
)
from tierkreis import Labels


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
    g.add(Output({"simple_eval_output": e("doubler_output")}))
    return g


def loop_body() -> GraphData:
    g = GraphData()
    a = g.add(Input("loop_acc"))("loop_acc")
    one = g.add(Const(1))(Labels.VALUE)
    N = g.add(Const(10))(Labels.VALUE)

    a_plus = g.add(Func("builtins.iadd", {"a": a, "b": one}))(Labels.VALUE)
    pred = g.add(Func("builtins.igt", {"a": N, "b": a_plus}))(Labels.VALUE)
    g.add(Output({"loop_acc": a_plus, "should_continue": pred}))
    return g


def simple_loop() -> GraphData:
    g = GraphData()
    six = g.add(Const(6))(Labels.VALUE)
    g_const = g.add(Const(loop_body()))(Labels.VALUE)
    loop = g.add(Loop(g_const, {"loop_acc": six}, "should_continue"))
    g.add(Output({"simple_loop_output": loop("loop_acc")}))
    return g


def simple_map() -> GraphData:
    g = GraphData()
    six = g.add(Const(6))(Labels.VALUE)
    Ns_const = g.add(Const(list(range(21))))(Labels.VALUE)
    Ns = g.add(Func("builtins.unfold_values", {Labels.VALUE: Ns_const}))
    doubler_const = g.add(Const(doubler_plus()))(Labels.VALUE)

    map_def = Map(
        doubler_const, Ns("")[0], "doubler_input", "doubler_output", {"intercept": six}
    )
    m = g.add(map_def)
    folded = g.add(Func("builtins.fold_values", {"values_glob": m("*")}))
    g.add(Output({"simple_map_output": folded(Labels.VALUE)}))
    return g


def simple_ifelse() -> GraphData:
    g = GraphData()
    pred = g.add(Input("pred"))("pred")
    one = g.add(Const(1))(Labels.VALUE)
    two = g.add(Const(2))(Labels.VALUE)
    out = g.add(IfElse(pred, one, two))(Labels.VALUE)
    g.add(Output({"simple_ifelse_output": out}))
    return g


def maps_in_series() -> GraphData:
    g = GraphData()
    zero = g.add(Const(0))(Labels.VALUE)
    Ns_const = g.add(Const(list(range(21))))(Labels.VALUE)
    Ns = g.add(Func("builtins.unfold_values", {Labels.VALUE: Ns_const}))
    doubler_const = g.add(Const(doubler_plus()))(Labels.VALUE)

    map_def = Map(
        doubler_const, Ns("")[0], "doubler_input", "doubler_output", {"intercept": zero}
    )
    m = g.add(map_def)

    map_def2 = Map(
        doubler_const, m("")[0], "doubler_input", "doubler_output", {"intercept": zero}
    )
    m2 = g.add(map_def2)
    folded = g.add(Func("builtins.fold_values", {"values_glob": m2("*")}))
    g.add(Output({"maps_in_series_output": folded(Labels.VALUE)}))
    return g


def map_with_str_keys() -> GraphData:
    g = GraphData()
    zero = g.add(Const(0))(Labels.VALUE)
    Ns_const = g.add(Const({"one": 1, "two": 2, "three": 3}))(Labels.VALUE)
    Ns = g.add(Func("builtins.unfold_dict", {Labels.VALUE: Ns_const}))
    doubler_const = g.add(Const(doubler_plus()))(Labels.VALUE)

    map_def = Map(
        doubler_const, Ns("")[0], "doubler_input", "doubler_output", {"intercept": zero}
    )
    m = g.add(map_def)
    folded = g.add(Func("builtins.fold_dict", {"values_glob": m("*")}))
    g.add(Output({"map_with_str_keys_output": folded(Labels.VALUE)}))
    return g


def factorial() -> GraphData:
    g = GraphData()
    minus_one = g.add(Const(-1))(Labels.VALUE)
    one = g.add(Const(1))(Labels.VALUE)
    n = g.add(Input("n"))("n")
    fac = g.add(Input("factorial"))("factorial")

    pred = g.add(Func("builtins.igt", {"a": n, "b": one}))(Labels.VALUE)

    n_minus_one = g.add(Func("builtins.iadd", {"a": minus_one, "b": n}))(Labels.VALUE)
    rec = g.add(Eval(fac, {"n": n_minus_one, "factorial": fac}))("factorial_output")
    if_true = g.add(Func("builtins.itimes", {"a": n, "b": rec}))(Labels.VALUE)

    if_false = g.add(Const(1))(Labels.VALUE)

    out = g.add(IfElse(pred, if_true, if_false))(Labels.VALUE)
    g.add(Output({"factorial_output": out}))
    return g
