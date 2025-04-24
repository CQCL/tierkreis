from dataclasses import dataclass, field
from typing import Any, Callable, Literal

from pydantic import BaseModel, RootModel
from tierkreis.controller.data.location import Loc, OutputLoc

Jsonable = Any
PortID = str


@dataclass
class Func:
    function_name: str
    inputs: dict[PortID, OutputLoc]
    type: Literal["function"] = field(default="function")


@dataclass
class Eval:
    body: OutputLoc
    inputs: dict[PortID, OutputLoc]
    type: Literal["eval"] = field(default="eval")


@dataclass
class Loop:
    body: OutputLoc
    inputs: dict[PortID, OutputLoc]
    tag_port: PortID  # Used to check break or continue
    bound_port: PortID  # Variable that is allowed to change
    type: Literal["loop"] = field(default="loop")


@dataclass
class Map:
    body: OutputLoc
    input_idx: Loc
    input_port: PortID
    output_port: PortID
    inputs: dict[PortID, OutputLoc]
    type: Literal["map"] = field(default="map")


@dataclass
class Const:
    value: Jsonable
    inputs: dict[PortID, OutputLoc] = field(default_factory=lambda: {})
    type: Literal["const"] = field(default="const")


@dataclass
class Input:
    name: str
    inputs: dict[PortID, OutputLoc] = field(default_factory=lambda: {})
    type: Literal["input"] = field(default="input")


@dataclass
class Output:
    inputs: dict[PortID, OutputLoc]
    type: Literal["output"] = field(default="output")


NodeDef = Map | Func | Eval | Loop | Const | Input | Output
NodeDefModel = RootModel[NodeDef]


class GraphData(BaseModel):
    nodes: dict[Loc, NodeDef] = {}
    outputs: dict[Loc, set[PortID]] = {}

    def add(self, node: NodeDef) -> Callable[[PortID], OutputLoc]:
        idx = len(self.nodes)
        loc = Loc().N(idx)
        self.nodes[loc] = node
        self.outputs[loc] = set()

        match node.type:
            case "map":
                self.outputs[node.input_idx].add("*")
            case _:
                pass

        for i, port in node.inputs.values():
            self.outputs[i].add(port)

        return lambda k: (loc, k)


@dataclass
class NodeRunData:
    node_location: Loc
    node: NodeDef
    output_list: list[PortID]
