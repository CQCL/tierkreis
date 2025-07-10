from typing import NamedTuple
from tierkreis.builtins.stubs import iadd, igt, itimes
from tierkreis.controller.data.core import EmptyModel
from tierkreis.builder import GraphBuilder
from tierkreis.controller.data.models import TKR


class DoublerInput(NamedTuple):
    doubler_input: TKR[int]
    intercept: TKR[int]


class CDoublerOutput(NamedTuple):
    a: TKR[int]
    value: TKR[int]


def ctyped_doubler_plus():
    g = GraphBuilder(DoublerInput, CDoublerOutput)
    two = g.const(2)
    mul = g.task(itimes(a=g.inputs.doubler_input, b=two))
    out = g.task(iadd(a=mul, b=g.inputs.intercept))
    g.outputs(CDoublerOutput(a=g.inputs.doubler_input, value=out))
    return g


def typed_doubler_plus():
    g = GraphBuilder(DoublerInput, TKR[int])
    two = g.const(2)
    mul = g.task(itimes(a=g.inputs.doubler_input, b=two))
    out = g.task(iadd(a=mul, b=g.inputs.intercept))
    g.outputs(out)
    return g


class TypedEvalOutputs(NamedTuple):
    typed_eval_output: TKR[int]


def typed_eval():
    g = GraphBuilder(EmptyModel, TypedEvalOutputs)
    zero = g.const(0)
    six = g.const(6)
    doubler_const = g.graph_const(typed_doubler_plus())
    e = g.eval(doubler_const, DoublerInput(doubler_input=six, intercept=zero))
    g.outputs(TypedEvalOutputs(typed_eval_output=e))
    return g


class LoopBodyInput(NamedTuple):
    loop_acc: TKR[int]


class LoopBodyOutput(NamedTuple):
    loop_acc: TKR[int]
    should_continue: TKR[bool]


def loop_body():
    g = GraphBuilder(LoopBodyInput, LoopBodyOutput)
    one = g.const(1)
    N = g.const(10)
    a_plus = g.task(iadd(a=g.inputs.loop_acc, b=one))
    pred = g.task(igt(a=N, b=a_plus))
    g.outputs(LoopBodyOutput(loop_acc=a_plus, should_continue=pred))
    return g


class TypedLoopOutput(NamedTuple):
    typed_loop_output: TKR[int]


def typed_loop():
    g = GraphBuilder(EmptyModel, TypedLoopOutput)
    six = g.const(6)
    g_const = g.graph_const(loop_body())
    loop = g.loop(g_const, LoopBodyInput(loop_acc=six), "should_continue")
    g.outputs(TypedLoopOutput(typed_loop_output=loop.loop_acc))
    return g


class TypedMapOutput(NamedTuple):
    typed_map_output: TKR[list[int]]


def typed_map():
    g = GraphBuilder(EmptyModel, TypedMapOutput)
    six = g.const(6)
    Ns = g.const(list(range(21)))
    ins = g.map(Ns, lambda n: DoublerInput(doubler_input=n, intercept=six))
    doubler_const = g.graph_const(typed_doubler_plus())
    m = g.map(ins, doubler_const)
    g.outputs(TypedMapOutput(typed_map_output=m))
    return g


def typed_destructuring():
    g = GraphBuilder(EmptyModel, TypedMapOutput)
    six = g.const(6)
    Ns = g.const(list(range(21)))
    ins = g.map(Ns, lambda n: DoublerInput(doubler_input=n, intercept=six))
    doubler_const = g.graph_const(ctyped_doubler_plus())
    m = g.map(ins, doubler_const)
    mout = g.map(m, lambda x: x.value)
    g.outputs(TypedMapOutput(typed_map_output=mout))
    return g
