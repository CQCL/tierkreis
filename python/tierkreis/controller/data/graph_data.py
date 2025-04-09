from dataclasses import dataclass, field
from typing import Any, Literal
from pydantic import BaseModel

from tierkreis.core import Labels

Jsonable = Any
PortID = str
NodeIndex = int
OutputLoc = tuple[NodeIndex, PortID]
ValueRef = tuple[NodeIndex, PortID]


@dataclass
class Func:
    function_name: str
    inputs: dict[PortID, ValueRef]
    outputs: list[PortID]
    type: Literal["function"] = field(default_factory=lambda: "function")


@dataclass
class Eval:
    graph: OutputLoc
    inputs: dict[PortID, ValueRef]
    outputs: list[PortID]
    type: Literal["eval"] = field(default_factory=lambda: "eval")


@dataclass
class Loop:
    body: OutputLoc
    inputs: dict[PortID, ValueRef]
    tag_port: PortID  # Used to check break or continue
    output_port: PortID  # Variable that is allowed to change
    type: Literal["loop"] = field(default_factory=lambda: "loop")
    outputs: list[PortID] = field(default_factory=lambda: [Labels.VALUE])


@dataclass
class Map:
    value_locs: list[OutputLoc]
    body_loc: OutputLoc
    inputs: dict[PortID, ValueRef]
    outputs: list[PortID]
    type: Literal["map"] = field(default_factory=lambda: "map")


@dataclass
class Const:
    value: Jsonable
    outputs: list[PortID]
    inputs: dict[PortID, ValueRef] = field(default_factory=lambda: {})
    type: Literal["const"] = field(default_factory=lambda: "const")


@dataclass
class Input:
    name: str
    outputs: list[PortID]
    inputs: dict[PortID, ValueRef] = field(default_factory=lambda: {})
    type: Literal["input"] = field(default_factory=lambda: "input")


@dataclass
class Output:
    inputs: dict[PortID, ValueRef]
    outputs: list[PortID]
    type: Literal["output"] = field(default_factory=lambda: "output")


NodeDef = Func | Eval | Loop | Map | Const | Input | Output


class GraphData(BaseModel):
    nodes: list[NodeDef] = []

    def add(self, node: NodeDef) -> dict[PortID, ValueRef]:
        idx = len(self.nodes)
        self.nodes.append(node)
        return {k: (idx, k) for k in node.outputs}
