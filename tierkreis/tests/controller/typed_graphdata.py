from pydantic import BaseModel
from tests.tkr_builtins import iadd, itimes
from tierkreis.controller.data.core import TypedValueRef
from tierkreis.controller.data.graph import GraphBuilder


class DoublerInput(BaseModel):
    doubler_input: TypedValueRef[int]
    intercept: TypedValueRef[int]


class DoublerOutput(BaseModel):
    doubler_output: TypedValueRef[int]


def typed_doubler_plus() -> GraphBuilder[DoublerInput, DoublerOutput]:
    g = GraphBuilder[DoublerInput, DoublerOutput]()
    ins = g.inputs(DoublerInput)
    two = g.const(2)
    mul = g.fn(itimes(a=ins.doubler_input, b=two))
    out = g.fn(iadd(a=mul, b=ins.intercept))
    return g.outputs(DoublerOutput(doubler_output=out))


class EmptyInputs(BaseModel):
    pass


class TypedEvalOutputs(BaseModel):
    typed_eval_output: TypedValueRef[int]


def typed_eval() -> GraphBuilder[EmptyInputs, TypedEvalOutputs]:
    g = GraphBuilder[EmptyInputs, TypedEvalOutputs]()
    zero = g.const(0)
    six = g.const(6)
    doubler_const = g.const(typed_doubler_plus())
    e = g.eval(
        doubler_const, DoublerInput(doubler_input=six, intercept=zero), DoublerOutput
    )
    return g.outputs(TypedEvalOutputs(typed_eval_output=e.doubler_output))
