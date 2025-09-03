from typing import NamedTuple
from tierkreis.builtins.stubs import iadd, igt, itimes, tuple_impl, untuple, mod
from tierkreis.controller.data.core import EmptyModel
from tierkreis.builder import GraphBuilder
from tierkreis.controller.data.models import TKR


class DoublerInput(NamedTuple):
    x: TKR[int]
    intercept: TKR[int]


class DoublerOutput(NamedTuple):
    a: TKR[int]
    value: TKR[int]


def typed_doubler_plus_multi():
    g = GraphBuilder(DoublerInput, DoublerOutput)
    mul = g.task(itimes(a=g.inputs.x, b=g.const(2)))
    out = g.task(iadd(a=mul, b=g.inputs.intercept))
    g.outputs(DoublerOutput(a=g.inputs.x, value=out))
    return g


def typed_doubler_plus():
    g = GraphBuilder(DoublerInput, TKR[int])
    mul = g.task(itimes(a=g.inputs.x, b=g.const(2)))
    out = g.task(iadd(a=mul, b=g.inputs.intercept))
    g.outputs(out)
    return g


class TypedEvalOutputs(NamedTuple):
    typed_eval_output: TKR[int]


def typed_eval():
    g = GraphBuilder(EmptyModel, TypedEvalOutputs)
    e = g.eval(typed_doubler_plus(), DoublerInput(x=g.const(6), intercept=g.const(0)))
    g.outputs(TypedEvalOutputs(typed_eval_output=e))
    return g


class LoopBodyInput(NamedTuple):
    loop_acc: TKR[int]


class LoopBodyOutput(NamedTuple):
    loop_acc: TKR[int]
    should_continue: TKR[bool]


def loop_body():
    g = GraphBuilder(LoopBodyInput, LoopBodyOutput)
    a_plus = g.task(iadd(a=g.inputs.loop_acc, b=g.const(1)))
    pred = g.task(igt(a=g.const(10), b=a_plus))
    g.outputs(LoopBodyOutput(loop_acc=a_plus, should_continue=pred))
    return g


class TypedLoopOutput(NamedTuple):
    typed_loop_output: TKR[int]


def typed_loop():
    g = GraphBuilder(EmptyModel, TypedLoopOutput)
    loop = g.loop(loop_body(), LoopBodyInput(loop_acc=g.const(6)))
    g.outputs(TypedLoopOutput(typed_loop_output=loop.loop_acc))
    return g


class TypedMapOutput(NamedTuple):
    typed_map_output: TKR[list[int]]


def typed_map():
    g = GraphBuilder(EmptyModel, TypedMapOutput)
    Ns = g.const(list(range(21)))
    ins = g.map(lambda n: DoublerInput(x=n, intercept=g.const(6)), Ns)
    m = g.map(typed_doubler_plus(), ins)
    g.outputs(TypedMapOutput(typed_map_output=m))
    return g


def typed_destructuring():
    g = GraphBuilder(EmptyModel, TypedMapOutput)
    Ns = g.const(list(range(21)))
    ins = g.map(lambda n: DoublerInput(x=n, intercept=g.const(6)), Ns)
    m = g.map(typed_doubler_plus_multi(), ins)
    mout = g.map(lambda x: x.value, m)
    g.outputs(TypedMapOutput(typed_map_output=mout))
    return g


def tuple_untuple():
    g = GraphBuilder(EmptyModel, TKR[int])
    t = g.task(tuple_impl(g.const(1), g.const(2)))
    ut = g.task(untuple(t))
    g.outputs(g.task(iadd(ut.a, ut.b)))
    return g


def factorial():
    g = GraphBuilder(TKR[int], TKR[int])
    pred = g.task(igt(g.inputs, g.const(1)))
    n_minus_one = g.task(iadd(g.const(-1), g.inputs))
    rec = g.eval(g.ref(), n_minus_one)
    out = g.ifelse(pred, g.task(itimes(g.inputs, rec)), g.const(1))
    g.outputs(out)
    return g


class GCDInput(NamedTuple):
    a: TKR[int]
    b: TKR[int]


def gcd():
    g = GraphBuilder(GCDInput, TKR[int])

    pred = g.task(igt(g.inputs.b, g.const(0)))
    a_mod_b = g.task(mod(g.inputs.a, g.inputs.b))
    rec = g.eval(g.ref(), GCDInput(a=g.inputs.b, b=a_mod_b))

    g.outputs(g.ifelse(pred, rec, g.inputs.a))
    return g
