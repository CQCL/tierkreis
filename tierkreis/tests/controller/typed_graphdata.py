from typing import Callable
from pydantic import BaseModel
from tests.tkr_builtins import iadd, igt, itimes
from tierkreis.controller.data.core import EmptyModel, PortID, TypedValueRef
from tierkreis.controller.data.graph import GraphBuilder


class DoublerInput(BaseModel):
    doubler_input: TypedValueRef[int]
    intercept: TypedValueRef[int]


class DoublerOutput(BaseModel):
    doubler_output: TypedValueRef[int]


def typed_doubler_plus() -> GraphBuilder[DoublerInput, DoublerOutput]:
    g = GraphBuilder(DoublerInput)
    two = g.const(2)
    mul = g.fn(itimes(a=g.inputs.doubler_input, b=two))
    out = g.fn(iadd(a=mul, b=g.inputs.intercept))
    return g.outputs(DoublerOutput(doubler_output=out))


class TypedEvalOutputs(BaseModel):
    typed_eval_output: TypedValueRef[int]


def typed_eval() -> GraphBuilder[EmptyModel, TypedEvalOutputs]:
    g = GraphBuilder()
    zero = g.const(0)
    six = g.const(6)
    doubler_const = g.graph_const(typed_doubler_plus())
    e = g.eval(doubler_const, DoublerInput(doubler_input=six, intercept=zero))
    return g.outputs(TypedEvalOutputs(typed_eval_output=e.doubler_output))


class LoopBodyInput(BaseModel):
    loop_acc: TypedValueRef[int]


class LoopBodyOutput(BaseModel):
    loop_acc: TypedValueRef[int]
    should_continue: TypedValueRef[bool]


def loop_body() -> GraphBuilder[LoopBodyInput, LoopBodyOutput]:
    g = GraphBuilder(LoopBodyInput)
    one = g.const(1)
    N = g.const(10)
    a_plus = g.fn(iadd(a=g.inputs.loop_acc, b=one))
    pred = g.fn(igt(a=N, b=a_plus))
    return g.outputs(LoopBodyOutput(loop_acc=a_plus, should_continue=pred))


class TypedLoopOutput(BaseModel):
    typed_loop_output: TypedValueRef[int]


def typed_loop() -> GraphBuilder[EmptyModel, TypedLoopOutput]:
    g = GraphBuilder()
    six = g.const(6)
    g_const = g.graph_const(loop_body())
    loop = g.loop(g_const, LoopBodyInput(loop_acc=six), "should_continue")
    return g.outputs(TypedLoopOutput(typed_loop_output=loop.loop_acc))


class TypedMapOutput(BaseModel):
    typed_map_output: TypedValueRef[list[int]]


def typed_map() -> GraphBuilder[EmptyModel, TypedMapOutput]:
    g = GraphBuilder()
    six = g.const(6)
    Ns_const = g.const(list(range(21)))
    Ns = g.unfold_list(Ns_const)
    doubler_inputs: Callable[[PortID], DoublerInput] = lambda n: DoublerInput(
        doubler_input=Ns(n), intercept=six
    )
    doubler_const = g.graph_const(typed_doubler_plus())
    m = g.map(doubler_const, doubler_inputs, "doubler_output")
    m_ints: Callable[[PortID], TypedValueRef[int]] = lambda x: m(x).doubler_output
    folded = g.fold_list(m_ints)
    return g.outputs(TypedMapOutput(typed_map_output=folded))
