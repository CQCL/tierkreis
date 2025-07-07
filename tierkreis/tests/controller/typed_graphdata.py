from typing import NamedTuple
from tierkreis.builtins.stubs import iadd, igt, itimes
from tierkreis.controller.data.core import EmptyModel, TKRRef
from tierkreis.builder import GraphBuilder
from tierkreis.controller.data.types import TBool, TInt, TList


class DoublerInput(NamedTuple):
    doubler_input: TInt
    intercept: TInt


def typed_doubler_plus():
    g = GraphBuilder(DoublerInput, TInt)
    two = g.const(2, TInt)
    mul = g.fn(itimes(a=g.inputs.doubler_input, b=two))
    out = g.fn(iadd(a=mul, b=g.inputs.intercept))
    g.outputs(out)
    return g


class TypedEvalOutputs(NamedTuple):
    typed_eval_output: TInt


def typed_eval():
    g = GraphBuilder(EmptyModel, TypedEvalOutputs)
    zero = g.const(0, TInt)
    six = g.const(6, TInt)
    doubler_const = g.graph_const(typed_doubler_plus())
    e = g.eval(doubler_const, DoublerInput(doubler_input=six, intercept=zero))
    g.outputs(TypedEvalOutputs(typed_eval_output=e))
    return g


class LoopBodyInput(NamedTuple):
    loop_acc: TInt


class LoopBodyOutput(NamedTuple):
    loop_acc: TInt
    should_continue: TBool


def loop_body():
    g = GraphBuilder(LoopBodyInput, LoopBodyOutput)
    one = g.const(1, TInt)
    N = g.const(10, TInt)
    a_plus = g.fn(iadd(a=g.inputs.loop_acc, b=one))
    pred = g.fn(igt(a=N, b=a_plus))
    g.outputs(LoopBodyOutput(loop_acc=a_plus, should_continue=pred))
    return g


class TypedLoopOutput(NamedTuple):
    typed_loop_output: TInt


def typed_loop():
    g = GraphBuilder(EmptyModel, TypedLoopOutput)
    six = g.const(6, TInt)
    g_const = g.graph_const(loop_body())
    loop = g.loop(g_const, LoopBodyInput(loop_acc=six), "should_continue")
    g.outputs(TypedLoopOutput(typed_loop_output=loop.loop_acc))
    return g


class TypedMapOutput(NamedTuple):
    typed_map_output: TList[TInt]


def typed_map():
    g = GraphBuilder(EmptyModel, TypedMapOutput)
    six = g.const(6, TInt)
    Ns_const = g.const(list(range(21)), TList[TInt])
    Ns = g.unfold_list(Ns_const)
    doubler_inputs = Ns.map(lambda n: DoublerInput(doubler_input=n, intercept=six))
    doubler_const = g.graph_const(typed_doubler_plus())
    m = g.map(doubler_const, doubler_inputs)
    folded = g.fold_list(m)
    g.outputs(TypedMapOutput(typed_map_output=folded))
    return g
