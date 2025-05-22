from dataclasses import dataclass, field
from typing import Callable, Literal, assert_never

from pydantic import BaseModel, RootModel, Field
from tierkreis import Labels
from tierkreis.controller.data.core import Jsonable
from tierkreis.controller.data.core import PortID
from tierkreis.controller.data.core import NodeIndex
from tierkreis.controller.data.core import ValueRef
from tierkreis.controller.data.location import OutputLoc
from tierkreis.exceptions import TierkreisError


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
    value_refs: list[ValueRef] = Field(exclude=True, default=[])

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

    def func(self, name: str, inputs: dict[str, int] | None = None) -> "GraphData":
        inputs = {k: self.value_refs[v] for k, v in inputs.items()} if inputs else {}
        self.value_refs.append(self.add(Func(name, inputs))(Labels.VALUE))
        return self

    def eval(self, body: "GraphData", n_inputs: int = 0) -> "GraphData":
        if len(self.nodes) < n_inputs:
            raise ValueError("Cannot add an eval, not enough nodes.")
        inputs = {f"{x}": self.value_refs[-(n_inputs + x) - 1] for x in range(n_inputs)}
        self.value_refs.append(self.add(Eval(body, inputs))(Labels.VALUE))
        return self

    def loop(
        self,
        body: "GraphData",
        loop_condition: str,
        inputs: dict[str, int] | None = None,
    ) -> "GraphData":
        l_body = self.add(Const(body))(Labels.VALUE)
        inputs = {k: self.value_refs[v] for k, v in inputs.items()} if inputs else {}
        self.value_refs.append(
            self.add(Loop(l_body, inputs, loop_condition))(Labels.VALUE)
        )
        return self

    def map(self, body: "GraphData", n_inputs: int = 0) -> "GraphData":
        if len(self.nodes) < n_inputs:
            raise ValueError("Cannot add an eval, not enough nodes.")
        inputs = {f"{x}": self.value_refs[-(n_inputs + x) - 1] for x in range(n_inputs)}
        m_body = self.const(body)

        map_def = Map(
            m_body, self.value_refs[-1][0], Labels.VALUE, Labels.VALUE, inputs
        )
        self.value_refs.append(self.add(map_def)(Labels.VALUE))
        return self

    def const(self, value: Jsonable) -> "GraphData":
        self.value_refs.append(self.add(Const(value))(Labels.VALUE))
        return self

    def ifelse(self) -> "GraphData":
        if len(self.nodes) < 3:
            raise ValueError("Cannot add an eifelse, not enough nodes.")
        self.value_refs.append(
            self.add(
                IfElse(self.value_refs[-3], self.value_refs[-2], self.value_refs[-1])
            )
        )
        return self

    def efelse(self) -> "GraphData":
        if len(self.nodes) < 3:
            raise ValueError("Cannot add an eifelse, not enough nodes.")
        self.value_refs.append(
            self.add(
                EagerIfElse(
                    self.value_refs[-3], self.value_refs[-2], self.value_refs[-1]
                )
            )
        )
        return self

    def input(self, name: str = Labels.VALUE) -> "GraphData":
        self.value_refs.append(self.add(Input(name))(name))
        return self

    def output(self, outputs: str | dict[str, int] = Labels.VALUE) -> "GraphData":
        # multi outputs not supported yet
        if len(self.nodes) == 0:
            raise ValueError("Cannot add an output to an empty graph.")
        if isinstance(outputs, dict):
            outputs = {k: self.value_refs[v] for k, v in outputs.items()}
            self.value_refs.append(self.add(Output(outputs)))
        else:
            self.value_refs.append(self.add(Output({outputs: self.value_refs[-1]})))
        return self
