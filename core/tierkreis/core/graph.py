from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from tierkreis.core.types import TierkreisType
import tierkreis.core.protos.tierkreis.graph as pg
import typing
from typing import Optional, cast
import betterproto

if typing.TYPE_CHECKING:
    from tierkreis.core.values import TierkreisValue


class GraphNode(ABC):
    @abstractmethod
    def to_proto(self) -> pg.Node:
        pass

    @staticmethod
    def from_proto(node: pg.Node) -> GraphNode:
        name, out_node = betterproto.which_one_of(node, "node")

        if name == "const":
            return ConstNode(cast(TierkreisValue, out_node))
        elif name == "box":
            return BoxNode(cast(Graph, out_node))
        elif name == "function":
            return FunctionNode(cast(str, out_node))
        elif name == "input":
            return InputNode()
        elif name == "output":
            return OutputNode()
        else:
            raise ValueError("Unknown protobuf node type: {}", name)


@dataclass(frozen=True)
class ConstNode(GraphNode):
    value: TierkreisValue

    def to_proto(self) -> pg.Node:
        return pg.Node(const=self.value.to_proto())


@dataclass(frozen=True)
class FunctionNode(GraphNode):
    function: str

    def to_proto(self) -> pg.Node:
        return pg.Node(function=self.function)


@dataclass(frozen=True)
class BoxNode(GraphNode):
    graph: Graph

    def to_proto(self) -> pg.Node:
        return pg.Node(box=self.graph.to_proto())


@dataclass(frozen=True)
class InputNode(GraphNode):
    def to_proto(self) -> pg.Node:
        return pg.Node(input=pg.Empty())


@dataclass(frozen=True)
class OutputNode(GraphNode):
    def to_proto(self) -> pg.Node:
        return pg.Node(output=pg.Empty())


@dataclass(frozen=True)
class NodePort:
    node: str
    port: str


@dataclass
class GraphEdge:
    source: NodePort
    target: NodePort
    type: Optional[TierkreisType]

    def to_proto(self) -> pg.Edge:
        if self.type is None:
            edge_type = None
        else:
            edge_type = self.type.to_proto()

        return pg.Edge(
            port_from=self.source.port,
            node_from=self.source.node,
            port_to=self.target.port,
            node_to=self.target.node,
            edge_type=cast(pg.Type, edge_type),
        )

    @staticmethod
    def from_proto(edge: pg.Edge) -> GraphEdge:
        return GraphEdge(
            source=NodePort(
                node=edge.node_from,
                port=edge.port_from,
            ),
            target=NodePort(node=edge.node_to, port=edge.port_to),
            type=TierkreisType.from_proto(edge.edge_type),
        )


@dataclass
class Graph:
    nodes: dict[str, GraphNode]
    edges: list[GraphEdge]

    def to_proto(self) -> pg.Graph:
        return pg.Graph(
            nodes={name: node.to_proto() for name, node in self.nodes.items()},
            edges=[edge.to_proto() for edge in self.edges],
        )

    @staticmethod
    def from_proto(graph: pg.Graph) -> "Graph":
        return Graph(
            nodes={
                name: GraphNode.from_proto(node) for name, node in graph.nodes.items()
            },
            edges=[GraphEdge.from_proto(edge) for edge in graph.edges],
        )
