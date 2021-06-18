"""Utilities for building tierkreis graphs."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Tuple, cast

import networkx as nx  # type: ignore
import tierkreis.core.protos.tierkreis.graph as pg
from tierkreis.core.types import TierkreisType
from tierkreis.core.values import TierkreisValue
import betterproto

# import graphviz as gv  # type: ignore

FunctionID = str

SIGNATURE: Dict[
    FunctionID, Tuple[Dict[str, TierkreisType], Dict[str, TierkreisType]]
] = dict()


@dataclass
class TierkreisNode(ABC):
    @abstractmethod
    def inputs(self) -> Dict[str, TierkreisType]:
        pass

    @abstractmethod
    def outputs(self) -> Dict[str, TierkreisType]:
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

    @abstractmethod
    def to_proto(self) -> pg.Node:
        pass

    @staticmethod
    def from_proto(node: pg.Node) -> "TierkreisNode":
        name, out_node = betterproto.which_one_of(node, "node")

        if name == "const":
            return ConstNode(cast(TierkreisValue, out_node))
        elif name == "box":
            return BoxNode(cast(TierkreisGraph, out_node))
        elif name == "function":
            return FunctionNode(cast(FunctionID, out_node))
        elif name == "input":
            return InputNode()
        elif name == "output":
            return OutputNode()
        else:
            raise ValueError("Unknown protobuf node type: {}", name)


@dataclass
class ConstNode(TierkreisNode):
    value: TierkreisValue

    def inputs(self) -> Dict[str, TierkreisType]:
        return dict()

    def outputs(self) -> Dict[str, TierkreisType]:
        # TODO return "unknown type"
        return NotImplemented

    def to_proto(self) -> pg.Node:
        return pg.Node(const=self.value.to_proto())


@dataclass
class InputNode(TierkreisNode):
    _inputs: Dict[str, TierkreisType] = field(default_factory=dict)

    def inputs(self) -> Dict[str, TierkreisType]:
        return dict()

    def outputs(self) -> Dict[str, TierkreisType]:
        return self._inputs

    def to_proto(self) -> pg.Node:
        return pg.Node(input=pg.Empty())


@dataclass
class OutputNode(TierkreisNode):
    _outputs: Dict[str, TierkreisType] = field(default_factory=dict)

    def inputs(self) -> Dict[str, TierkreisType]:
        return self._outputs

    def outputs(self) -> Dict[str, TierkreisType]:
        return dict()

    def to_proto(self) -> pg.Node:
        return pg.Node(output=pg.Empty())


@dataclass
class BoxNode(TierkreisNode):
    graph: "TierkreisGraph"

    def inputs(self) -> Dict[str, TierkreisType]:
        return self.graph.inputs

    def outputs(self) -> Dict[str, TierkreisType]:
        return self.graph.outputs

    def to_proto(self) -> pg.Node:
        return pg.Node(box=self.graph.to_proto())


@dataclass
class FunctionNode(TierkreisNode):
    function: FunctionID

    def inputs(self) -> Dict[str, TierkreisType]:
        return SIGNATURE[self.function][0]

    def outputs(self) -> Dict[str, TierkreisType]:
        return SIGNATURE[self.function][1]

    def to_proto(self) -> pg.Node:
        return pg.Node(function=self.function)


# @dataclass
# class TierkreisEdge:
#     source: NodePort
#     target: NodePort
#     type: Optional[TierkreisType]

#     def to_proto(self) -> pg.Edge:
#         if self.type is None:
#             edge_type = None
#         else:
#             edge_type = self.type.to_proto()

#         return pg.Edge(
#             port_from=self.source.port,
#             node_from=self.source.node,
#             port_to=self.target.port,
#             node_to=self.target.node,
#             edge_type=cast(pg.Type, edge_type),
#         )

#     @staticmethod
#     def from_proto(edge: pg.Edge) -> GraphEdge:
#         return GraphEdge(
#             source=NodePort(
#                 node=edge.node_from,
#                 port=edge.port_from,
#             ),
#             target=NodePort(node=edge.node_to, port=edge.port_to),
#             type=TierkreisType.from_proto(edge.edge_type),
#         )


class TierkreisGraph:
    """Builder for tierkreis graphs."""

    def __init__(self) -> None:
        self._graph = nx.MultiDiGraph()
        self._graph.add_node(self.input_node_name, node_info=InputNode())
        self._graph.add_node(self.output_node_name, node_info=OutputNode())

        self._input_types: Dict[str, TierkreisType] = dict()
        self._output_types: Dict[str, TierkreisType] = dict()

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
    def inputs(self) -> Dict[str, TierkreisType]:
        return self._input_types

    @property
    def outputs(self) -> Dict[str, TierkreisType]:
        return self._output_types

    def add_node(self, name: str, node: TierkreisNode):
        self._graph.add_node(name, node_info=node)
        return name

    def add_function_node(
        self,
        name: str,
        function: str,
    ) -> str:
        return self.add_node(name, FunctionNode(function))

    def add_const(self, name: str, value: Any) -> str:
        tkval = (
            value
            if isinstance(value, TierkreisValue)
            else TierkreisValue.from_python(value)
        )
        return self.add_node(name, ConstNode(tkval))

    def add_box(self, name: str, graph: "TierkreisGraph") -> str:
        return self.add_node(name, BoxNode(graph))

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

    def to_proto(self) -> pg.Graph:
        return NotImplemented

    @staticmethod
    def from_proto(graph: pg.Graph) -> "TierkreisGraph":
        return NotImplemented
