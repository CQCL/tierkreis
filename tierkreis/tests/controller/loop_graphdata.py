from tierkreis.controller.data.graph import Const, Func, GraphData, Input, Loop, Output
from tierkreis import Labels


def _loop_body_multiple_acc() -> GraphData:
    g = GraphData()

    acc = g.add(Input("acc"))("acc")
    acc2 = g.add(Input("acc2"))("acc2")
    acc3 = g.add(Input("acc3"))("acc3")

    one = g.add(Const(1))(Labels.VALUE)
    two = g.add(Const(2))(Labels.VALUE)
    three = g.add(Const(3))(Labels.VALUE)
    five = g.add(Const(5))(Labels.VALUE)

    should_continue = g.add(Func("builtins.igt", {"a": five, "b": acc}))(Labels.VALUE)

    new_acc = g.add(Func("builtins.iadd", {"a": acc, "b": one}))(Labels.VALUE)
    new_acc2 = g.add(Func("builtins.iadd", {"a": acc2, "b": two}))(Labels.VALUE)
    new_acc3 = g.add(Func("builtins.iadd", {"a": acc3, "b": three}))(Labels.VALUE)

    g.add(
        Output(
            {
                "should_continue": should_continue,
                "acc": new_acc,
                "acc2": new_acc2,
                "acc3": new_acc3,
            }
        )
    )

    return g


def loop_multiple_acc() -> GraphData:
    g = GraphData()

    acc = g.add(Const(0))(Labels.VALUE)
    acc2 = g.add(Const(0))(Labels.VALUE)
    acc3 = g.add(Const(0))(Labels.VALUE)

    body_const = g.add(Const(_loop_body_multiple_acc()))(Labels.VALUE)

    loop = g.add(
        Loop(body_const, {"acc": acc, "acc2": acc2, "acc3": acc3}, "should_continue")
    )

    g.add(Output({"acc": loop("acc"), "acc2": loop("acc2"), "acc3": loop("acc3")}))

    return g
