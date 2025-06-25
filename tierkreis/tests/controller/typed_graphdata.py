from typing import NamedTuple
from tierkreis.builtins.stubs import iadd, igt, itimes
from tierkreis.controller.data.core import EmptyModel, TKRRef
from tierkreis.controller.data.graph import GraphBuilder


class DoublerInput(NamedTuple):
    doubler_input: TKRRef[int]
    intercept: TKRRef[int]


def typed_doubler_plus() -> GraphBuilder[DoublerInput, TKRRef[int]]:
    g = GraphBuilder(DoublerInput)
    two = g.const(2)
    mul = g.fn(itimes(a=g.inputs.doubler_input, b=two))
    out = g.fn(iadd(a=mul, b=g.inputs.intercept))
    return g.outputs(out)


class TypedEvalOutputs(NamedTuple):
    typed_eval_output: TKRRef[int]


def typed_eval() -> GraphBuilder[EmptyModel, TypedEvalOutputs]:
    g = GraphBuilder()
    zero = g.const(0)
    six = g.const(6)
    doubler_const = g.graph_const(typed_doubler_plus())
    e = g.eval(doubler_const, DoublerInput(doubler_input=six, intercept=zero))
    return g.outputs(TypedEvalOutputs(typed_eval_output=e))


class LoopBodyInput(NamedTuple):
    loop_acc: TKRRef[int]


class LoopBodyOutput(NamedTuple):
    loop_acc: TKRRef[int]
    should_continue: TKRRef[bool]


def loop_body() -> GraphBuilder[LoopBodyInput, LoopBodyOutput]:
    g = GraphBuilder(LoopBodyInput)
    one = g.const(1)
    N = g.const(10)
    a_plus = g.fn(iadd(a=g.inputs.loop_acc, b=one))
    pred = g.fn(igt(a=N, b=a_plus))
    return g.outputs(LoopBodyOutput(loop_acc=a_plus, should_continue=pred))


class TypedLoopOutput(NamedTuple):
    typed_loop_output: TKRRef[int]


def typed_loop() -> GraphBuilder[EmptyModel, TypedLoopOutput]:
    g = GraphBuilder()
    six = g.const(6)
    g_const = g.graph_const(loop_body())
    loop = g.loop(g_const, LoopBodyInput(loop_acc=six), "should_continue")
    return g.outputs(TypedLoopOutput(typed_loop_output=loop.loop_acc))


class TypedMapOutput(NamedTuple):
    typed_map_output: TKRRef[list[int]]


def typed_map() -> GraphBuilder[EmptyModel, TypedMapOutput]:
    g = GraphBuilder()
    six = g.const(6)
    Ns_const = g.const(list(range(21)))
    Ns = g.unfold_list(Ns_const)
    doubler_inputs = Ns.map(lambda n: DoublerInput(doubler_input=n, intercept=six))
    doubler_const = g.graph_const(typed_doubler_plus())
    m = g.map(doubler_const, doubler_inputs)
    folded = g.fold_list(m)
    return g.outputs(TypedMapOutput(typed_map_output=folded))
