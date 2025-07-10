from dataclasses import dataclass
from typing import Any, Callable, Protocol, overload

from tierkreis.controller.data.core import EmptyModel, PortID, ValueRef
from tierkreis.controller.data.graph import (
    Const,
    Eval,
    Func,
    GraphData,
    Input,
    Loop,
    Map,
    Output,
)
from tierkreis.controller.data.models import (
    TKR,
    TModel,
    TNamedModel,
    dict_from_tmodel,
    model_fields,
    init_tmodel,
)
from tierkreis.controller.data.types import PType


@dataclass
class TList[T: TModel]:
    """A list of models."""

    _value: T


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

    def _unfold_list[T: PType](self, ref: TKR[list[T]]) -> TList[TKR[T]]:
        ins = (ref.node_index, ref.port_id)
        idx, _ = self.data.add(Func("builtins.unfold_values", {"value": ins}))("dummy")
        return TList(TKR[T](idx, "*"))

    def _fold_list[T: PType](self, refs: TList[TKR[T]]) -> TKR[list[T]]:
        value_ref = refs._value.node_index, refs._value.port_id
        idx, _ = self.data.add(
            Func("builtins.fold_values", {"values_glob": value_ref})
        )("dummy")
        return TKR[list[T]](idx, "value")

    def map_fn_single_in[A: PType, B: TModel](
        self, aes: TKR[list[A]], body: Callable[[TKR[A]], B]
    ) -> "TList[B]":
        tlist = self._unfold_list(aes)
        return TList(body(TKR(tlist._value.node_index, "*")))

    def map_fn_single_out[A: TModel, B: PType](
        self, aes: TList[A], body: Callable[[A], TKR[B]]
    ) -> TKR[list[B]]:
        return self._fold_list(TList(body(aes._value)))

    def map_graph_single_out[A: TModel, B: PType](
        self, aes: TList[A], body: TypedGraphRef[A, TKR[B]]
    ) -> TKR[list[B]]:
        return self._fold_list(self.map_graph_full(aes, body))

    def map_graph_full[A: TModel, B: TModel](
        self, aes: TList[A], body: TypedGraphRef[A, B]
    ) -> TList[B]:
        ins = dict_from_tmodel(aes._value)
        first_ref = next(x for x in ins.values() if x[1] == "*")
        idx, _ = self.data.add(Map(body.graph_ref, first_ref[0], "x", "x", ins))("x")

        refs = [(idx, s + "-*") for s in model_fields(body.outputs_type)]
        return TList(init_tmodel(body.outputs_type, refs))

    @overload
    def map[A: PType, B: TModel](
        self, aes: TKR[list[A]], body: Callable[[TKR[A]], B]
    ) -> "TList[B]": ...

    @overload
    def map[A: TModel, B: PType](
        self, aes: TList[A], body: Callable[[A], TKR[B]]
    ) -> TKR[list[B]]: ...

    @overload
    def map[A: TModel, B: PType](  # type: ignore # overlapping overload warning
        self, aes: TList[A], body: TypedGraphRef[A, TKR[B]]
    ) -> TKR[list[B]]: ...

    @overload
    def map[A: TModel, B: TModel](
        self, aes: TList[A], body: TypedGraphRef[A, B]
    ) -> TList[B]: ...

    def map(self, aes: Any, body: Any) -> Any:
        if isinstance(body, TypedGraphRef) and isinstance(
            body.outputs_type, TNamedModel
        ):
            return self.map_graph_full(aes, body)
        elif isinstance(body, TypedGraphRef):
            return self.map_graph_single_out(aes, body)
        elif isinstance(aes, TList):
            return self.map_fn_single_out(aes, body)
        elif isinstance(aes, TKR):
            return self.map_fn_single_in(aes, body)
