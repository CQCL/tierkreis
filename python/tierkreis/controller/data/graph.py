from dataclasses import dataclass, field
from typing import Any, Callable, Literal

from pydantic import BaseModel

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
    tag_port: PortID  # Used to check break or continue
    output_port: PortID  # Variable that is allowed to change
    type: Literal["loop"] = field(default="loop")


@dataclass
class Map:
    body: ValueRef
    value_refs: list[ValueRef]
    inputs: dict[PortID, ValueRef]
    type: Literal["map"] = field(default="map")


@dataclass
class Const:
    value: Jsonable
    inputs: dict[PortID, ValueRef] = field(default_factory=lambda: {})
    type: Literal["const"] = field(default="const")


@dataclass
class Input:
    name: str
    inputs: dict[PortID, ValueRef] = field(default_factory=lambda: {})
    type: Literal["input"] = field(default="input")


@dataclass
class Output:
    inputs: dict[PortID, ValueRef]
    type: Literal["output"] = field(default="output")


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

    def map(self, map: Map) -> list[ValueRef]:
        idx = len(self.nodes)
        self.add(map)
        return [(idx, str(i)) for i, _ in enumerate(map.value_refs)]
