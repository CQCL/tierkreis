from dataclasses import dataclass, field
import json
import logging
from typing import Any, Callable, Generic, Literal, assert_never, cast
from tierkreis.controller.data.models import TModel
from typing_extensions import TypeVar
from pydantic import BaseModel, RootModel
from tierkreis.controller.data.core import (
    EmptyModel,
    Jsonable,
    TKRList,
    TKRModel,
    TKRType,
    TKRRef,
    ref_from_tkr_type,
    annotations_from_tkrref,
)
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
