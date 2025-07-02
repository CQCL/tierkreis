from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import json
import logging
from typing import Any, Callable, Generic, Literal, Protocol, Unpack, assert_never
from uuid import uuid4
from tierkreis.controller.data.refs import (
    IntRef,
    ModelRef,
    TypeRef,
    inputs_from_modelref,
    is_typeref,
    reftype_from_ttype,
)
from typing_extensions import TypeVar
from pydantic import BaseModel, RootModel
from tierkreis.controller.data.core import EmptyModel, TModel, TType
from tierkreis.controller.data.core import PortID
from tierkreis.controller.data.core import NodeIndex
from tierkreis.controller.data.core import ValueRef
from tierkreis.controller.data.location import OutputLoc
from tierkreis.exceptions import TierkreisError
from collections import namedtuple

logger = logging.getLogger(__name__)


@dataclass
class Func:
    function_name: str
    inputs: dict[PortID, ValueRef]
    type: Literal["function"] = field(default="function")


@dataclass
class Eval:
    graph: ValueRef
    inputs: dict[PortID, ValueRef]
    type: Literal["eval"] = field(default="eval")


@dataclass
class Loop:
    body: ValueRef
    inputs: dict[PortID, ValueRef]
    continue_port: PortID  # The port that specifies if the loop should continue.
    type: Literal["loop"] = field(default="loop")


@dataclass
class Map:
    body: ValueRef
    input_idx: NodeIndex
    in_port: PortID  # Input port for the Map.body
    out_port: PortID  # Output port for the Map.body
    inputs: dict[PortID, ValueRef]
    type: Literal["map"] = field(default="map")


@dataclass
class Const:
    value: Any
    inputs: dict[PortID, ValueRef] = field(default_factory=lambda: {})
    type: Literal["const"] = field(default="const")


@dataclass
class IfElse:
    pred: ValueRef
    if_true: ValueRef
    if_false: ValueRef
    type: Literal["ifelse"] = field(default="ifelse")
    inputs: dict[PortID, ValueRef] = field(default_factory=lambda: {})


@dataclass
class EagerIfElse:
    pred: ValueRef
    if_true: ValueRef
    if_false: ValueRef
    type: Literal["eifelse"] = field(default="eifelse")
    inputs: dict[PortID, ValueRef] = field(default_factory=lambda: {})


@dataclass
class Input:
    name: str
    inputs: dict[PortID, ValueRef] = field(default_factory=lambda: {})
    type: Literal["input"] = field(default="input")


@dataclass
class Output:
    inputs: dict[PortID, ValueRef]
    type: Literal["output"] = field(default="output")


NodeDef = Func | Eval | Loop | Map | Const | IfElse | EagerIfElse | Input | Output
NodeDefModel = RootModel[NodeDef]


class GraphData(BaseModel):
    nodes: list[NodeDef] = []
    node_outputs: list[set[PortID]] = []
    fixed_inputs: dict[PortID, OutputLoc] = {}
    graph_inputs: set[PortID] = set()
    graph_output_idx: NodeIndex | None = None

    def input(self, name: str) -> ValueRef:
        return self.add(Input(name))(name)

    def const(self, value: Any) -> ValueRef:
        return self.add(Const(value))("value")

    def func(
        self, function_name: str, inputs: dict[PortID, ValueRef]
    ) -> Callable[[PortID], ValueRef]:
        return self.add(Func(function_name, inputs))

    def eval(
        self, graph: ValueRef, inputs: dict[PortID, ValueRef]
    ) -> Callable[[PortID], ValueRef]:
        return self.add(Eval(graph, inputs))

    def loop(
        self, body: ValueRef, inputs: dict[PortID, ValueRef], continue_port: PortID
    ) -> Callable[[PortID], ValueRef]:
        return self.add(Loop(body, inputs, continue_port))

    def map(
        self,
        body: ValueRef,
        input_idx: NodeIndex,
        in_port: PortID,
        out_port: PortID,
        inputs: dict[PortID, ValueRef],
    ) -> Callable[[PortID], ValueRef]:
        return self.add(Map(body, input_idx, in_port, out_port, inputs))

    def output(self, inputs: dict[PortID, ValueRef]) -> None:
        self.add(Output(inputs))

    def add(self, node: NodeDef) -> Callable[[PortID], ValueRef]:
        idx = len(self.nodes)
        self.nodes.append(node)
        self.node_outputs.append(set())

        match node.type:
            case "output":
                if self.graph_output_idx is not None:
                    raise TierkreisError(
                        f"Graph already has output at index {self.graph_output_idx}"
                    )

                self.graph_output_idx = idx
            case "ifelse" | "eifelse":
                self.node_outputs[node.pred[0]].add(node.pred[1])
                self.node_outputs[node.if_true[0]].add(node.if_true[1])
                self.node_outputs[node.if_false[0]].add(node.if_false[1])
            case "input":
                self.graph_inputs.add(node.name)
            case "const" | "eval" | "function" | "loop" | "map":
                pass
            case _:
                assert_never(node)

        for i, port in node.inputs.values():
            self.node_outputs[i].add(port)

        return lambda k: (idx, k)

    def output_idx(self) -> NodeIndex:
        idx = self.graph_output_idx
        if idx is None:
            raise TierkreisError("Graph has no output index.")

        node = self.nodes[idx]
        if node.type != "output":
            raise TierkreisError(f"Expected output node at {idx} found {node}")

        return idx

    def remaining_inputs(self, provided_inputs: set[PortID]) -> set[PortID]:
        fixed_inputs = set(self.fixed_inputs.keys())
        if fixed_inputs & provided_inputs:
            raise TierkreisError(
                f"Fixed inputs {fixed_inputs}"
                f" should not intersect provided inputs {provided_inputs}."
            )

        actual_inputs = fixed_inputs.union(provided_inputs)
        return self.graph_inputs - actual_inputs


def ref_from_ttype(g: GraphData | NodeIndex, t: TType) -> TypeRef:
    if is_typeref(t):
        return t

    match g:
        case NodeIndex():
            idx, port = g, "value"
        case GraphData():
            idx, port = g.add(Const(t))("value")
        case _:
            assert_never(g)

    ref = reftype_from_ttype(type(t))
    return ref.from_value_ref(idx, port)


def modelref_from_tmodel(g: GraphData, t: TModel) -> ModelRef:
    if hasattr(t, "_asdict"):
        fields: list[str] | None = getattr(t, "_fields", None)
        if fields is None:
            raise TierkreisError("TModel must be NamedTuple.")

        NT = namedtuple(f"new_tuple_{uuid4().hex}", fields)  # type: ignore
        return NT(*[ref_from_ttype(g, x) for x in t])

    else:
        return ref_from_ttype(g, t)


class Function[Out: TModel](Protocol):
    @property
    @abstractmethod
    def namespace(self) -> str: ...

    @staticmethod
    @abstractmethod
    def out(idx: NodeIndex) -> Out: ...


Inputs = TypeVar("Inputs", bound=TModel, default=EmptyModel)
Outputs = TypeVar("Outputs", bound=TModel, default=EmptyModel)


@dataclass
class TypedGraphRef(Generic[Inputs, Outputs]):
    graph_ref: ValueRef
    inputs_type: type[Inputs]
    outputs_type: type[Outputs]


In = TypeVar("In", bound=tuple[TType, ...], contravariant=True)


class GraphBuilder(Generic[Inputs, Outputs]):
    outputs_type: type
    inputs: Inputs

    def __init__(self, inputs_type: type[Inputs] = EmptyModel):
        self.data = GraphData()
        self.inputs_type = inputs_type
        self.inputs = self.inputs_type(
            **{
                k: IntRef.from_value_ref(*self.data.add(Input(k))(k))
                for k in self.inputs_type._fields
            }
        )
        print(self.inputs)

    def get_data(self) -> GraphData:
        return self.data

    def outputs[Out: TModel](self, outputs: Out) -> "GraphBuilder[Inputs, Out]":
        ref = modelref_from_tmodel(self.data, outputs)
        print(ref)
        ins = inputs_from_modelref(ref)
        self.data.add(Output(inputs=ins))
        builder = GraphBuilder[self.inputs_type, Out](self.inputs_type)
        builder.data = GraphData(**json.loads(self.data.model_dump_json()))
        builder.outputs_type = type(outputs)
        return builder

    def graph_const[A: TModel, B: TModel](
        self, graph: "GraphBuilder[A, B]"
    ) -> TypedGraphRef[A, B]:
        idx, port = self.data.add(Const(graph.data))("value")
        return TypedGraphRef[A, B](
            graph_ref=(idx, port),
            inputs_type=graph.inputs_type,
            outputs_type=graph.outputs_type,
        )

    def fn[Out: TModel](self, f: Function[Out]) -> Out:
        print(self.inputs)
        print(f.ins_type(*ins).a.node_index)
        name = f"{f.namespace}.{f.__class__.__name__}"
        ins = {k: v.value_ref() for k, v in f.to_dict(self.data).items()}
        idx, _ = self.data.add(Func(name, ins))("dummy")
        return f.out(idx)

    def eval[A: TModel, B: TModel](self, body: TypedGraphRef[A, B], a: A) -> B:
        refs = modelref_from_tmodel(self.data, a)
        ins = inputs_from_modelref(refs)
        g = body.graph_ref
        Out = body.outputs_type
        idx, _ = self.data.add(Eval(g, ins))("dummy")
        return Out()

    # def loop[A: TKRModel, B: TKRModel](
    #     self, body: TypedGraphRef[A, B], a: A, continue_port: PortID
    # ) -> B:
    #     ins = {k: (v[0], v[1]) for k, v in annotations_from_tkrref(a).items()}
    #     g = body.graph_ref
    #     Out = body.outputs_type
    #     idx, _ = self.data.add(Loop(g, ins, continue_port))("dummy")
    #     return ref_from_tkr_type(Out, lambda _: idx)

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
