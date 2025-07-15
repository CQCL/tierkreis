from dataclasses import dataclass
from inspect import isclass
from typing import Any, Callable, Generic, Protocol, TypeVar, overload

from tierkreis.controller.data.core import EmptyModel, ValueRef
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


Inputs = TypeVar("Inputs", bound=TModel, contravariant=True)
Outputs = TypeVar("Outputs", bound=TModel, covariant=True)


@dataclass
class TypedGraphRef(Generic[Inputs, Outputs]):
    graph_ref: ValueRef
    outputs_type: type[Outputs]


class LoopOutput(TNamedModel, Protocol):
    @property
    def should_continue(self) -> TKR[bool]: ...


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

    def _graph_const[A: TModel, B: TModel](
        self, graph: "GraphBuilder[A, B]"
    ) -> TypedGraphRef[A, B]:
        idx, port = self.data.add(Const(graph.data.model_dump()))("value")
        return TypedGraphRef[A, B](
            graph_ref=(idx, port), outputs_type=graph.outputs_type
        )

    def task[Out: TModel](self, f: Function[Out]) -> Out:
        name = f"{f.namespace}.{f.__class__.__name__}"
        ins = dict_from_tmodel(f)
        idx, _ = self.data.add(Func(name, ins))("dummy")
        OutModel = f.out()
        outputs = [(idx, x) for x in model_fields(OutModel)]
        return init_tmodel(OutModel, outputs)

    @overload
    def eval[A: TModel, B: TModel](self, body: TypedGraphRef[A, B], a: A) -> B: ...
    @overload
    def eval[A: TModel, B: TModel](self, body: "GraphBuilder[A, B]", a: A) -> B: ...
    def eval[A: TModel, B: TModel](
        self, body: "GraphBuilder[A,B] | TypedGraphRef", a: Any
    ) -> Any:
        if isinstance(body, GraphBuilder):
            body = self._graph_const(body)

        idx, _ = self.data.add(Eval(body.graph_ref, dict_from_tmodel(a)))("dummy")
        outputs = [(idx, x) for x in model_fields(body.outputs_type)]
        return init_tmodel(body.outputs_type, outputs)

    @overload
    def loop[A: TModel, B: LoopOutput](self, body: TypedGraphRef[A, B], a: A) -> B: ...
    @overload
    def loop[A: TModel, B: LoopOutput](self, body: "GraphBuilder[A, B]", a: A) -> B: ...
    def loop[A: TModel, B: LoopOutput](
        self, body: "TypedGraphRef[A, B] |GraphBuilder[A, B]", a: A
    ) -> B:
        if isinstance(body, GraphBuilder):
            body = self._graph_const(body)

        g = body.graph_ref
        idx, _ = self.data.add(Loop(g, dict_from_tmodel(a), "should_continue"))("dummy")
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

    def _map_fn_single_in[A: PType, B: TModel](
        self, aes: TKR[list[A]], body: Callable[[TKR[A]], B]
    ) -> "TList[B]":
        tlist = self._unfold_list(aes)
        return TList(body(TKR(tlist._value.node_index, "*")))

    def _map_fn_single_out[A: TModel, B: PType](
        self, aes: TList[A], body: Callable[[A], TKR[B]]
    ) -> TKR[list[B]]:
        return self._fold_list(TList(body(aes._value)))

    def _map_graph_single_out[A: TModel, B: PType](
        self, aes: TList[A], body: TypedGraphRef[A, TKR[B]]
    ) -> TKR[list[B]]:
        return self._fold_list(self._map_graph_full(aes, body))

    def _map_graph_single_in[A: PType, B: TModel](
        self, aes: TKR[list[A]], body: TypedGraphRef[TKR[A], B]
    ) -> TList[B]:
        return self._map_graph_full(self._unfold_list(aes), body)

    def _map_graph_full[A: TModel, B: TModel](
        self, aes: TList[A], body: TypedGraphRef[A, B]
    ) -> TList[B]:
        ins = dict_from_tmodel(aes._value)
        idx, _ = self.data.add(Map(body.graph_ref, "x", ins))("x")

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
    def map[A: TModel, B: PType](  # type: ignore # overlapping overload warning
        self, aes: TList[A], body: "GraphBuilder[A, TKR[B]]"
    ) -> TKR[list[B]]: ...

    @overload
    def map[A: TModel, B: TModel](
        self, aes: TList[A], body: TypedGraphRef[A, B]
    ) -> TList[B]: ...

    @overload
    def map[A: PType, B: TModel](
        self, aes: TKR[list[A]], body: "GraphBuilder[TKR[A], B]"
    ) -> TList[B]: ...

    @overload
    def map[A: PType, B: TModel](
        self, aes: TKR[list[A]], body: TypedGraphRef[TKR[A], B]
    ) -> TList[B]: ...

    @overload
    def map[A: TModel, B: TModel](
        self, aes: TList[A], body: "GraphBuilder[A, B]"
    ) -> TList[B]: ...

    def map(
        self, aes: TKR | TList, body: TypedGraphRef | Callable | "GraphBuilder"
    ) -> Any:
        if isinstance(body, GraphBuilder):
            body = self._graph_const(body)

        if isinstance(body, Callable):
            if isinstance(aes, TList):
                return self._map_fn_single_out(aes, body)
            elif isinstance(aes, TKR):
                return self._map_fn_single_in(aes, body)

        if isinstance(aes, TKR):
            aes = self._unfold_list(aes)

        out = self._map_graph_full(aes, body)

        if not isclass(body.outputs_type) or not issubclass(
            body.outputs_type, TNamedModel
        ):
            out = self._fold_list(out)

        return out
