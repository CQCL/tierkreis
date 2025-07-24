from tierkreis import Labels
from tierkreis_core import GraphData


def _loop_body_multiple_acc() -> GraphData:
    g = GraphData()

    acc = g.input("acc1")
    acc2 = g.input("acc2")
    acc3 = g.input("acc3")

    one = g.const(1)
    two = g.const(2)
    three = g.const(3)
    five = g.const(5)

    should_continue = g.func("builtins.igt", {"a": five, "b": acc})("value")

    new_acc = g.func("builtins.iadd", {"a": acc, "b": one})("value")
    new_acc2 = g.func("builtins.iadd", {"a": acc2, "b": two})("value")
    new_acc3 = g.func("builtins.iadd", {"a": acc3, "b": three})("value")

    g.output(
        {
            "should_continue": should_continue,
            "acc": new_acc,
            "acc2": new_acc2,
            "acc3": new_acc3,
        }
    )

    return g


def loop_multiple_acc() -> GraphData:
    g = GraphData()

    acc = g.const(0)
    acc2 = g.const(0)
    acc3 = g.const(0)

    body_const = g.const(_loop_body_multiple_acc())

    loop = g.loop(
        body_const, {"acc": acc, "acc2": acc2, "acc3": acc3}, "should_continue"
    )

    g.output({"acc": loop("acc"), "acc2": loop("acc2"), "acc3": loop("acc3")})

    return g
