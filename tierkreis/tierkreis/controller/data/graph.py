from dataclasses import dataclass, field
import json
import logging
from typing import Callable, Generic, Literal, assert_never
from typing_extensions import TypeVar
from pydantic import BaseModel, RootModel
from tierkreis.controller.data.core import EmptyModel, Jsonable, TypedValueRef
from tierkreis.controller.data.core import PortID
from tierkreis.controller.data.core import NodeIndex
from tierkreis.controller.data.core import ValueRef, Function
from tierkreis.controller.data.location import OutputLoc
from tierkreis.exceptions import TierkreisError

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
    value: Jsonable
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

    def const(self, value: Jsonable) -> ValueRef:
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


Inputs = TypeVar("Inputs", bound=BaseModel, default=EmptyModel)
Outputs = TypeVar("Outputs", bound=BaseModel, default=EmptyModel)


class TypedGraphRef(BaseModel, Generic[Inputs, Outputs]):
    graph_ref: TypedValueRef[GraphData]
    inputs_type: type[Inputs]
    outputs_type: type[Outputs]


class GraphBuilder(Generic[Inputs, Outputs]):
    outputs_type: type

    def __init__(self, inputs_type: type[Inputs] = EmptyModel):
        self.data = GraphData()
        self.inputs_type = inputs_type

        fields = {}
        for name, info in inputs_type.model_fields.items():
            idx, _ = self.data.add(Input(name))(name)
            fields[name] = info.annotation.from_nodeindex(idx, name)  # type: ignore

        self.inputs = inputs_type(**fields)

    def get_data(self) -> GraphData:
        return self.data

    def outputs[Out: BaseModel](self, outputs: Out) -> "GraphBuilder[Inputs, Out]":
        self.data.add(Output(inputs=outputs.model_dump()))
        builder = GraphBuilder[self.inputs_type, Out](self.inputs_type)
        builder.data = GraphData(**json.loads(self.data.model_dump_json()))
        builder.outputs_type = type(outputs)
        return builder

    def const[T](self, value: T) -> TypedValueRef[T]:
        idx, port = self.data.add(Const(value))("value")
        return TypedValueRef[T](idx, port)

    def graph_const[A: BaseModel, B: BaseModel](
        self, graph: "GraphBuilder[A, B]"
    ) -> TypedGraphRef[A, B]:
        idx, port = self.data.add(Const(graph.data))("value")
        return TypedGraphRef[A, B](
            graph_ref=TypedValueRef[GraphData](idx, port),
            inputs_type=graph.inputs_type,
            outputs_type=graph.outputs_type,
        )

    def fn[Out](self, f: Function[Out]) -> Out:
        reserved_fields = ["namespace", "out"]
        ins = {
            k: (v[0], v[1])
            for k, v in f.model_dump().items()
            if k not in reserved_fields
        }
        idx, _ = self.data.add(Func(f"{f.namespace}.{f.__class__.__name__}", ins))("*")
        return f.out(idx)

    def eval[A: BaseModel, B: BaseModel](self, body: TypedGraphRef[A, B], a: A) -> B:
        ins = {k: (v[0], v[1]) for k, v in a.model_dump().items()}
        g = body.graph_ref
        Out = body.outputs_type
        idx, _ = self.data.add(Eval(g, ins))("*")
        fields = {  # type: ignore
            name: info.annotation.from_nodeindex(idx, name)  # type: ignore
            for name, info in Out.model_fields.items()  # type: ignore
        }
        return Out(**fields)

    def loop[A: BaseModel, B: BaseModel](
        self, body: TypedGraphRef[A, B], a: A, continue_port: PortID
    ) -> B:
        ins = {k: (v[0], v[1]) for k, v in a.model_dump().items()}
        g = body.graph_ref
        Out = body.outputs_type
        idx, _ = self.data.add(Loop(g, ins, continue_port))("*")
        fields = {  # type: ignore
            name: info.annotation.from_nodeindex(idx, name)  # type: ignore
            for name, info in Out.model_fields.items()  # type: ignore
        }
        return Out(**fields)
