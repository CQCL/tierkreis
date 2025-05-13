from dataclasses import dataclass, field
from typing import Any, Callable, Literal, assert_never

from pydantic import BaseModel, RootModel
from tierkreis.exceptions import TierkreisError

Jsonable = Any
PortID = str
NodeIndex = int
ValueRef = tuple[NodeIndex, PortID]


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
class Input:
    name: str
    inputs: dict[PortID, ValueRef] = field(default_factory=lambda: {})
    type: Literal["input"] = field(default="input")


@dataclass
class Output:
    inputs: dict[PortID, ValueRef]
    type: Literal["output"] = field(default="output")


NodeDef = Func | Eval | Loop | Map | Const | IfElse | Input | Output
NodeDefModel = RootModel[NodeDef]


class GraphData(BaseModel):
    nodes: list[NodeDef] = []
    outputs: list[set[PortID]] = []
    graph_output_idx: NodeIndex | None = None

    def add(self, node: NodeDef) -> Callable[[PortID], ValueRef]:
        idx = len(self.nodes)
        self.nodes.append(node)
        self.outputs.append(set())

        match node.type:
            case "output":
                if self.graph_output_idx is not None:
                    raise TierkreisError(
                        f"Graph already has output at index {self.graph_output_idx}"
                    )

                self.graph_output_idx = idx
            case "ifelse":
                self.outputs[node.pred[0]].add(node.pred[1])
                self.outputs[node.if_true[0]].add(node.if_true[1])
                self.outputs[node.if_false[0]].add(node.if_false[1])
            case "const" | "eval" | "function" | "input" | "loop" | "map":
                pass
            case _:
                assert_never(node)

        for i, port in node.inputs.values():
            self.outputs[i].add(port)

        return lambda k: (idx, k)

    def output_idx(self) -> NodeIndex:
        idx = self.graph_output_idx
        if idx is None:
            raise TierkreisError("Graph has no output index.")

        node = self.nodes[idx]
        if node.type != "output":
            raise TierkreisError(f"Expected output node at {idx} found {node}")

        return idx
