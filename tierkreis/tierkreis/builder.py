from dataclasses import dataclass
from typing import Protocol

from tierkreis.controller.data.core import EmptyModel, PortID, ValueRef
from tierkreis.controller.data.graph import (
    Const,
    Eval,
    Func,
    GraphData,
    Input,
    Loop,
    Output,
)
from tierkreis.controller.data.models import (
    TModel,
    TNamedModel,
    dict_from_tmodel,
    model_fields,
    init_tmodel,
)
from tierkreis.controller.data.types import PType, TKR


class Function[Out](TNamedModel, Protocol):
    @property
    def namespace(self) -> str: ...

    @staticmethod
    def out() -> type[Out]: ...


@dataclass
class TypedGraphRef[Inputs: TModel, Outputs: TModel]:
    graph_ref: ValueRef
    outputs_type: type[Outputs]


class GraphBuilder[Inputs: TModel, Outputs: TModel]:
    outputs_type: type
    inputs: Inputs

    def __init__(
        self,
        inputs_type: type[Inputs] = EmptyModel,
        outputs_type: type[Outputs] = EmptyModel,
    ):
        self.data = GraphData()
        self.inputs_type = inputs_type
        self.outputs_type = outputs_type
        inputs = [self.data.add(Input(x))(x) for x in model_fields(inputs_type)]
        self.inputs = init_tmodel(self.inputs_type, inputs)

    def get_data(self) -> GraphData:
        return self.data

    def outputs(self, outputs: Outputs):
        self.data.add(Output(inputs=dict_from_tmodel(outputs)))

    def const[T: PType](self, value: T) -> TKR[T]:
        idx, port = self.data.add(Const(value))("value")
        return TKR[T](idx, port)

    def graph_const[A: TModel, B: TModel](
        self, graph: "GraphBuilder[A, B]"
    ) -> TypedGraphRef[A, B]:
        idx, port = self.data.add(Const(graph.data))("value")
        return TypedGraphRef[A, B](
            graph_ref=(idx, port), outputs_type=graph.outputs_type
        )

    def fn[Out: TModel](self, f: Function[Out]) -> Out:
        name = f"{f.namespace}.{f.__class__.__name__}"
        ins = dict_from_tmodel(f)
        idx, _ = self.data.add(Func(name, ins))("dummy")
        OutModel = f.out()
        outputs = [(idx, x) for x in model_fields(OutModel)]
        return init_tmodel(OutModel, outputs)

    def eval[A: TModel, B: TModel](self, body: TypedGraphRef[A, B], a: A) -> B:
        idx, _ = self.data.add(Eval(body.graph_ref, dict_from_tmodel(a)))("dummy")
        outputs = [(idx, x) for x in model_fields(body.outputs_type)]
        return init_tmodel(body.outputs_type, outputs)

    def loop[A: TModel, B: TModel](
        self, body: TypedGraphRef[A, B], a: A, continue_port: PortID
    ) -> B:
        g = body.graph_ref
        idx, _ = self.data.add(Loop(g, dict_from_tmodel(a), continue_port))("dummy")
        outputs = [(idx, x) for x in model_fields(body.outputs_type)]
        return init_tmodel(body.outputs_type, outputs)

    # def unfold_list[T: TKRType](self, ref: TKRRef[list[T]]) -> TKRList[TKRRef[T]]:
    #     idx, _ = self.data.add(Func("builtins.unfold_values", {"value": ref}))("dummy")
    #     return TKRList(TKRRef[T](idx, "*"))

    # def fold_list[T: TKRType](self, refs: TKRList[TKRRef[T]]) -> TKRRef[list[T]]:
    #     idx, port = refs.t
    #     idx, _ = self.data.add(
    #         Func("builtins.fold_values", {"values_glob": (idx, port)})
    #     )("dummy")
    #     return TKRRef[list[T]](idx, "value")

    # def map[A: TKRModel, B: TKRModel](
    #     self, body: TypedGraphRef[A, B], aes: TKRList[A]
    # ) -> TKRList[B]:
    #     a = aes.t
    #     ins = {k: (v[0], v[1]) for k, v in annotations_from_tkrref(a).items()}
    #     g = body.graph_ref
    #     first_ref = cast(TKRRef[Any], next(x for x in ins.values() if x[1] == "*"))
    #     idx, _ = self.data.add(Map(g, first_ref[0], "dummy", "dummy", ins))("dummy")

    #     Out = body.outputs_type
    #     return TKRList(
    #         ref_from_tkr_type(Out, lambda _: idx, name_fn=lambda s: s + "-*")
    #     )
