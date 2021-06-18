"""Utilities for building tierkreis graphs."""
from typing import IO, Dict, List, Optional, Set, Tuple, Type, Union
from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass, field
from tierkreis.core.protos.tierkreis.graph import Graph as ProtoGraph
from tierkreis.core import Value, encode_value, from_python_type
import networkx as nx  # type: ignore
import graphviz as gv  # type: ignore

TKType = Type
FunctionID = str

SIGNATURE: Dict[FunctionID, Tuple[Dict[str, TKType], Dict[str, TKType]]] = dict()


@dataclass
class TierkreisNode(ABC):
    @abstractmethod
    def inputs(self) -> Dict[str, TKType]:
        pass

    @abstractmethod
    def outputs(self) -> Dict[str, TKType]:
        pass

    @property
    def in_port(self) -> Enum:
        return Enum(
            type(self).__name__ + ".in_port", [(n, n) for n in self.inputs().keys()]
        )

    @property
    def out_port(self) -> Enum:
        return Enum(
            type(self).__name__ + ".out_port", [(n, n) for n in self.outputs().keys()]
        )


@dataclass
class Constant(TierkreisNode):
    value: Value

    def inputs(self) -> Dict[str, TKType]:
        return dict()

    def outputs(self) -> Dict[str, TKType]:
        return {"value": type(self.value)}


@dataclass
class Input(TierkreisNode):
    _inputs: Dict[str, TKType] = field(default_factory=dict)

    def inputs(self) -> Dict[str, TKType]:
        return dict()

    def outputs(self) -> Dict[str, TKType]:
        return self._inputs


@dataclass
class Output(TierkreisNode):
    _outputs: Dict[str, TKType] = field(default_factory=dict)

    def inputs(self) -> Dict[str, TKType]:
        return self._outputs

    def outputs(self) -> Dict[str, TKType]:
        return dict()


@dataclass
class Box(TierkreisNode):
    graph: "TierkreisGraph"

    def inputs(self) -> Dict[str, TKType]:
        return self.graph.inputs

    def outputs(self) -> Dict[str, TKType]:
        return self.graph.outputs


@dataclass
class Function(TierkreisNode):
    function: FunctionID

    def inputs(self) -> Dict[str, TKType]:
        return SIGNATURE[self.function][0]

    def outputs(self) -> Dict[str, TKType]:
        return SIGNATURE[self.function][1]


class TierkreisGraph:
    """Builder for tierkreis graphs."""

    def __init__(self) -> None:
        self._graph = nx.MultiDiGraph()
        self._graph.add_node(self.input_node_name, node_info=Input())
        self._graph.add_node(self.output_node_name, node_info=Output())

        self._input_types: Dict[str, TKType] = dict()
        self._output_types: Dict[str, TKType] = dict()

    @property
    def n_nodes(self) -> int:
        return len(self._graph)

    @property
    def input_node_name(self) -> str:
        return "input"

    @property
    def output_node_name(self) -> str:
        return "output"

    @property
    def inputs(self) -> Dict[str, TKType]:
        return self._input_types

    @property
    def outputs(self) -> Dict[str, TKType]:
        return self._output_types

    def add_node(self, name: str, node: TierkreisNode):
        self._graph.add_node(name, node_info=node)
        return name

    def add_function_node(
        self,
        name: str,
        function: str,
    ) -> str:
        return self.add_node(name, Function(function))

    def add_const(self, name: str, value: Value) -> str:
        return self.add_node(name, Constant(value))

    def add_box(self, name: str, graph: "TierkreisGraph") -> str:
        return self.add_node(name, Box(graph))

    @property
    def nodes(self) -> Dict[str, TierkreisNode]:
        # TODO make a dictionary view instead
        return {
            name: self._graph.nodes[name]["node_info"] for name in self._graph.nodes
        }

    # def add_edge(
    #     self,
    #     node_port_from: Tuple[str, str],
    #     node_port_to: Tuple[str, str],
    #     edge_type: Optional[Type] = None,
    # ):
    #     new_edge = pg.Edge()
    #     new_edge.node_from, new_edge.port_from = node_port_from
    #     new_edge.node_to, new_edge.port_to = node_port_to
    #     self._g.edges.append(new_edge)
    #     if edge_type is not None:
    #         new_edge.edge_type = from_python_type(edge_type)

    #     if node_port_from[0] == "input":
    #         self._input_types[node_port_from[1]] = edge_type
    #     if node_port_to[0] == "output":
    #         self._output_types[node_port_to[1]] = edge_type

    # def register_input(self, name: str, edge_type: Type, node_port: Tuple[str, str]):
    #     self._input_types[name] = edge_type
    #     self.add_edge((self.input_node, name), node_port, edge_type)

    # def register_output(self, name: str, edge_type: Type, node_port: Tuple[str, str]):
    #     self._output_types[name] = edge_type
    #     self.add_edge(node_port, (self.output_node, name), edge_type)

    # def incoming_edges(self, node: str) -> List[pg.Edge]:
    #     return [e for e in self._g.edges if e.node_to == node]

    # def outgoing_edges(self, node: str) -> List[pg.Edge]:
    #     return [e for e in self._g.edges if e.node_from == node]

    # def input_edges(self) -> List[pg.Edge]:
    #     return self.outgoing_edges(self.input_node)

    # def output_edges(self) -> List[pg.Edge]:
    #     return self.incoming_edges(self.output_node)

    # def remove_edge(
    #     self, node_port_from: Tuple[str, str], node_port_to: Tuple[str, str]
    # ) -> pg.Edge:

    #     edge = next(
    #         (
    #             e
    #             for e in self._g.edges
    #             if ((e.node_from, e.port_from), (e.node_to, e.port_to))
    #             == (node_port_from, node_port_to)
    #         )
    #     )
    #     self._g.edges.remove(edge)
    #     return edge

    # def get_type(self) -> Type:
    #     return type(
    #         "ProtoGraphBuilder",
    #         (ProtoGraphBuilder,),
    #         {"inputs": self._input_types, "outputs": self._output_types},
    #     )

    # def write_to_file(self, file_pointer: IO[bytes]):
    #     file_pointer.write(self._g.SerializeToString())

    # @classmethod
    # def read_from_file(cls, file_pointer: IO[bytes]) -> "ProtoGraphBuilder":
    #     new = cls()
    #     new._g.parse(file_pointer.read())
    #     return new
