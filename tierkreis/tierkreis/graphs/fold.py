from typing import NamedTuple, Protocol, Sequence
from tierkreis.builder import GraphBuilder, TypedGraphRef
from tierkreis.builtins.stubs import head, igt, impl_len
from tierkreis.controller.data.graph import GraphData
from tierkreis.controller.data.models import TKR, TNamedModel
from tierkreis.controller.data.types import PType


class FoldGraphOuterInputs[A: PType, B: PType](NamedTuple):
    func: TKR[GraphData]
    accum: TKR[B]
    values: TKR[Sequence[A]]


class FoldGraphOuterOutputs[A: PType, B: PType](NamedTuple):
    accum: TKR[B]
    values: TKR[Sequence[A]]
    should_continue: TKR[bool]


class InnerFuncInput[A: PType, B: PType](NamedTuple):
    accum: TKR[B]
    value: TKR[A]


def _fold_graph_outer[A: PType, B: PType]():
    g = GraphBuilder(FoldGraphOuterInputs[A, B], FoldGraphOuterOutputs[A, B])

    func = g.inputs.func
    accum = g.inputs.accum
    values = g.inputs.values

    values_len = g.task(impl_len(values))
    # True if there is more than one value in the list.
    non_empty = g.task(igt(values_len, g.const(0)))

    # Will only succeed if values is non-empty.
    headed = g.task(head(values))

    # Apply the function if we were able to pop off a value.
    tgd = TypedGraphRef[InnerFuncInput, TKR[B]](func.value_ref(), TKR[B])
    applied_next = g.eval(tgd, InnerFuncInput(accum, headed.head))

    next_accum = g.ifelse(non_empty, applied_next, accum)
    next_values = g.ifelse(non_empty, headed.rest, values)
    g.outputs(FoldGraphOuterOutputs(next_accum, next_values, non_empty))
    return g


class FoldGraphInputs[A: PType, B: PType](NamedTuple):
    initial: TKR[B]
    values: TKR[Sequence[tuple[A, B]]]


class FoldFunctionInput[A: PType, B: PType](TNamedModel, Protocol):
    @property
    def accum(self) -> TKR[B]: ...

    @property
    def value(self) -> TKR[A]: ...


# fold : {func: (b -> a -> b)} -> {initial: b} -> {values: list[a]} -> {value: b}
def fold_graph[A: PType, B: PType](func: GraphBuilder[FoldFunctionInput[A, B], TKR[B]]):
    g = GraphBuilder(FoldGraphInputs[A, B], TKR[B])
    foldfunc = g._graph_const(func)
    # TODO: include the computation inside the fold
    ins = FoldGraphOuterInputs(
        TKR(*foldfunc.graph_ref), g.inputs.initial, g.inputs.values
    )
    loop = g.loop(_fold_graph_outer(), ins)
    g.outputs(loop.accum)
    return g
