from typing import NamedTuple
from tierkreis.builtins.stubs import iadd, itimes
from tierkreis.controller.data.core import EmptyModel
from tierkreis.controller.data.graph import GraphBuilder


class DoublerInput(NamedTuple):
    doubler_input: int
    intercept: int


def typed_doubler_plus() -> GraphBuilder[DoublerInput, int]:
    g = GraphBuilder(DoublerInput, int)
    two = 2
    mul = g.fn(itimes(a=g.inputs.doubler_input, b=two))
    out = g.fn(iadd(a=mul, b=g.inputs.intercept))
    g.outputs(out)
    return g


class TypedEvalOutputs(NamedTuple):
    typed_eval_output: int


def typed_eval():
    g = GraphBuilder(EmptyModel, TypedEvalOutputs)
    doubler_const = g.graph_const(typed_doubler_plus())
    e = g.eval(doubler_const, DoublerInput(doubler_input=6, intercept=0))
    g.outputs(TypedEvalOutputs(typed_eval_output=e))
    return g


class LoopBodyInput(NamedTuple):
    loop_acc: int


class LoopBodyOutput(NamedTuple):
    loop_acc: int
    should_continue: bool


# def loop_body():
#     g = GraphBuilder(LoopBodyInput, LoopBodyOutput)
#     a_plus = g.fn(iadd(a=g.inputs.loop_acc, b=1))
#     pred = g.fn(igt(a=10, b=a_plus))
#     g.outputs(LoopBodyOutput(loop_acc=a_plus, should_continue=pred))
#     return g


# class TypedLoopOutput(NamedTuple):
#     typed_loop_output: int


# def typed_loop():
#     g = GraphBuilder(EmptyModel, TypedLoopOutput)
#     g_const = g.graph_const(loop_body())
#     loop = g.loop(g_const, LoopBodyInput(loop_acc=6), "should_continue")
#     g.outputs(TypedLoopOutput(typed_loop_output=loop.loop_acc))
#     return g


# class TypedMapOutput(NamedTuple):
#     typed_map_output: list[int]


# def typed_map():
#     g = GraphBuilder(EmptyModel, TypedMapOutput)
#     Ns = g.unfold_list(list(range(21)))
#     doubler_inputs = Ns.map(lambda n: DoublerInput(doubler_input=n, intercept=6))
#     doubler_const = g.graph_const(typed_doubler_plus())
#     m = g.map(doubler_const, doubler_inputs)
#     folded = g.fold_list(m)
#     g.outputs(TypedMapOutput(typed_map_output=folded))
#     return g
