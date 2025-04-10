from dataclasses import dataclass, field
from typing import Any, Callable, Literal
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
    type: Literal["function"] = field(default_factory=lambda: "function")


@dataclass
class Eval:
    graph: OutputLoc
    inputs: dict[PortID, ValueRef]
    type: Literal["eval"] = field(default_factory=lambda: "eval")


@dataclass
class Loop:
    body: OutputLoc
    inputs: dict[PortID, ValueRef]
    tag_port: PortID  # Used to check break or continue
    output_port: PortID  # Variable that is allowed to change
    type: Literal["loop"] = field(default_factory=lambda: "loop")


@dataclass
class Map:
    value_locs: list[OutputLoc]
    body_loc: OutputLoc
    inputs: dict[PortID, ValueRef]
    type: Literal["map"] = field(default_factory=lambda: "map")


@dataclass
class Const:
    value: Jsonable
    inputs: dict[PortID, ValueRef] = field(default_factory=lambda: {})
    type: Literal["const"] = field(default_factory=lambda: "const")


@dataclass
class Input:
    name: str
    inputs: dict[PortID, ValueRef] = field(default_factory=lambda: {})
    type: Literal["input"] = field(default_factory=lambda: "input")


@dataclass
class Output:
    inputs: dict[PortID, ValueRef]
    type: Literal["output"] = field(default_factory=lambda: "output")


NodeDef = Func | Eval | Loop | Map | Const | Input | Output


class GraphData(BaseModel):
    nodes: list[NodeDef] = []
    outputs: list[set[PortID]] = []

    def add(self, node: NodeDef) -> Callable[[PortID], ValueRef]:
        idx = len(self.nodes)
        self.nodes.append(node)
        self.outputs.append(set())

        for i, port in node.inputs.values():
            self.outputs[i].add(port)

        return lambda k: (idx, k)
