"""Utilities for building tierkreis graphs."""
import typing
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import (
    Any,
    Dict,
    Iterator,
    List,
    Optional,
    Set,
    Tuple,
    Type,
    Union,
    cast,
)

import betterproto
import graphviz as gv  # type: ignore
import networkx as nx  # type: ignore
import tierkreis.core.protos.tierkreis.graph as pg
from tierkreis.core.types import (
    TierkreisType,
    TypeScheme,
)
from tierkreis.core.values import T, TierkreisValue

FunctionID = str
PortID = str


@dataclass
class TierkreisFunction:
    name: str
    type_scheme: TypeScheme
    docs: str

    @classmethod
    def from_proto(cls, pr_entry: pg.SignatureEntry) -> "TierkreisFunction":
        return cls(
            pr_entry.name, TypeScheme.from_proto(pr_entry.type_scheme), pr_entry.docs
        )


@dataclass
class TierkreisNode(ABC):
    @abstractmethod
    def to_proto(self) -> pg.Node:
        pass

    @staticmethod
    def from_proto(node: pg.Node) -> "TierkreisNode":
        name, out_node = betterproto.which_one_of(node, "node")

        if name == "const":
            return ConstNode(cast(TierkreisValue, out_node))
        if name == "box":
            return BoxNode(cast(TierkreisGraph, out_node))
        if name == "function":
            return FunctionNode(cast(FunctionID, out_node))
        if name == "input":
            return InputNode()
        if name == "output":
            return OutputNode()
        raise ValueError(f"Unknown protobuf node type: {name}")


@dataclass
class InputNode(TierkreisNode):
    def to_proto(self) -> pg.Node:
        return pg.Node(input=pg.Empty())


@dataclass
class OutputNode(TierkreisNode):
    def to_proto(self) -> pg.Node:
        return pg.Node(output=pg.Empty())


@dataclass
class ConstNode(TierkreisNode):
    value: TierkreisValue

    def to_proto(self) -> pg.Node:
        return pg.Node(const=self.value.to_proto())


@dataclass
class BoxNode(TierkreisNode):
    graph: "TierkreisGraph"

    def to_proto(self) -> pg.Node:
        return pg.Node(box=self.graph.to_proto())


@dataclass
class FunctionNode(TierkreisNode):
    function_name: str

    def to_proto(self) -> pg.Node:
        return pg.Node(function=self.function_name)


class PortNotFound(Exception):
    pass


@dataclass
class Ports:

    _node_ref: "NodeRef"
    _ports: Set[str]
    _check_name: bool

    def __getattribute__(self, name: str) -> "NodePort":
        if name in super().__getattribute__("_ports") or not super().__getattribute__(
            "_check_name"
        ):
            return NodePort(super().__getattribute__("_node_ref"), PortID(name))
        raise PortNotFound(name)


class NodeRef:
    def __init__(
        self,
        name: str,
        out_ports: Set[str] = set(),
        restrict_ports: bool = False,
    ) -> None:
        self.name = name
        self.out = Ports(self, out_ports, restrict_ports)


@dataclass(frozen=True)
class NodePort:
    node_ref: NodeRef
    port: PortID


@dataclass
class TierkreisEdge:
    source: NodePort
    target: NodePort
    type: Optional[TierkreisType]

    def to_proto(self) -> pg.Edge:
        edge_type = None if self.type is None else self.type.to_proto()

        return pg.Edge(
            port_from=self.source.port,
            node_from=self.source.node_ref.name,
            port_to=self.target.port,
            node_to=self.target.node_ref.name,
            edge_type=cast(pg.Type, edge_type),
        )


class TierkreisGraph:
    """TierkreisGraph."""

    input_node_name: str = "input"
    output_node_name: str = "output"

    def __init__(self, name: Optional[str] = None) -> None:
        self.name = name
        self._graph = nx.MultiDiGraph()
        self._graph.add_node(self.input_node_name, node_info=InputNode())
        self._graph.add_node(self.output_node_name, node_info=OutputNode())
        self.output = NodeRef(self.output_node_name)
        self.input = NodeRef(self.input_node_name)

        self._name_counts = {name: 0 for name in ("const, box")}

    def inputs(self) -> List[str]:
        return [edge.source.port for edge in self.out_edges(self.input)]

    def outputs(self) -> List[str]:
        return [edge.target.port for edge in self.in_edges(self.output)]

    @property
    def n_nodes(self) -> int:
        return len(self._graph)

    def _get_fresh_name(self, name_class: str) -> str:
        if name_class not in self._name_counts:
            self._name_counts[name_class] = 0
        count = self._name_counts[name_class]
        suffix = f"_{count}" if count > 0 else ""

        self._name_counts[name_class] += 1
        return f"{name_class}{suffix}"

    def _add_node(
        self,
        node_ref: NodeRef,
        node: TierkreisNode,
        incoming_wires: Dict[str, Union[NodePort, NodeRef]],
    ) -> NodeRef:
        self._graph.add_node(node_ref.name, node_info=node)
        for target_port_name, source in incoming_wires.items():
            target = NodePort(node_ref, target_port_name)
            source = source if isinstance(source, NodePort) else source.out.value
            self.add_edge(source, target)

        return node_ref

    def add_node(
        self,
        _tk_function: Union[str, TierkreisFunction],
        _tk_node_name: Optional[str] = None,
        /,
        **kwargs: Union[NodePort, NodeRef],
    ) -> NodeRef:
        f_name = _tk_function if isinstance(_tk_function, str) else _tk_function.name
        if _tk_node_name is None:
            _tk_node_name = self._get_fresh_name(f_name)

        node = FunctionNode(f_name)
        if isinstance(_tk_function, str):
            node_ref = NodeRef(_tk_node_name)
        else:
            scheme_body = _tk_function.type_scheme.body
            outports = set(scheme_body.outputs.content.keys())
            restrict_outputs = scheme_body.outputs.rest is None
            if scheme_body.inputs.rest is None:
                for inport_name in kwargs:
                    if inport_name not in scheme_body.inputs.content:
                        raise PortNotFound(inport_name)

            node_ref = NodeRef(_tk_node_name, outports, restrict_outputs)
            # TODO check type

        return self._add_node(node_ref, node, kwargs)

    def add_const(self, value: Any, name: Optional[str] = None) -> NodeRef:
        if name is None:
            name = self._get_fresh_name("const")
        tkval = (
            value
            if isinstance(value, TierkreisValue)
            else TierkreisValue.from_python(value)
        )

        return self._add_node(NodeRef(name, {"value"}, True), ConstNode(tkval), {})

    def add_box(
        self,
        graph: "TierkreisGraph",
        name: Optional[str] = None,
        **kwargs: Union[NodePort, NodeRef],
    ) -> NodeRef:
        # TODO restrict to graph i/o
        if name is None:
            name = self._get_fresh_name("box")
        return self._add_node(NodeRef(name, set(), False), BoxNode(graph), kwargs)

    def nodes(self) -> Dict[str, TierkreisNode]:
        return {
            name: self._graph.nodes[name]["node_info"] for name in self._graph.nodes
        }

    def edges(self) -> List[TierkreisEdge]:
        return [
            cast(TierkreisEdge, edge_info[2])
            for edge_info in self._graph.edges(data="edge_info", keys=False)
        ]

    def __getitem__(self, key: Union[str, NodeRef]) -> TierkreisNode:
        name = key.name if isinstance(key, NodeRef) else key
        return self._graph.nodes[name]["node_info"]

    def add_edge(
        self,
        node_port_from: NodePort,
        node_port_to: NodePort,
        edge_type: Optional[Union[Type, TierkreisType]] = None,
    ) -> TierkreisEdge:
        tk_type = _get_edge(edge_type)

        edge = TierkreisEdge(node_port_from, node_port_to, tk_type)

        self._graph.add_edge(
            node_port_from.node_ref.name,
            node_port_to.node_ref.name,
            edge_info=edge,
        )
        return edge

    def set_outputs(self, **kwargs: Union[NodePort, NodeRef]) -> None:
        for out_name, port in kwargs.items():
            target = NodePort(self.output, out_name)
            source = port if isinstance(port, NodePort) else port.out.value
            self.add_edge(source, target)

    def in_edges(self, node: Union[NodeRef, str]) -> List[TierkreisEdge]:
        node_name = node if isinstance(node, str) else node.name
        return [
            cast(TierkreisEdge, edge_info[2])
            for edge_info in self._graph.in_edges(
                node_name, data="edge_info", keys=False
            )
        ]

    def out_edges(self, node: Union[NodeRef, str]) -> List[TierkreisEdge]:
        node_name = node if isinstance(node, str) else node.name
        return [
            cast(TierkreisEdge, edge_info[2])
            for edge_info in self._graph.out_edges(
                node_name, data="edge_info", keys=False
            )
        ]

    def to_proto(self) -> pg.Graph:
        pg_graph = pg.Graph()
        pg_graph.nodes = {
            node_name: node.to_proto()
            for node_name, node in cast(
                Iterator[Tuple[str, TierkreisNode]], self._graph.nodes(data="node_info")
            )
        }
        pg_graph.edges = [
            cast(TierkreisEdge, edge_info[2]).to_proto()
            for edge_info in self._graph.edges(data="edge_info", keys=False)
        ]
        return pg_graph

    @classmethod
    def from_proto(cls, pg_graph: pg.Graph) -> "TierkreisGraph":
        tk_graph = cls()
        # io_nodes = {tk_graph.input_node_name, tk_graph.output_node_name}
        for node_name, pg_node in pg_graph.nodes.items():
            tk_graph._add_node(
                NodeRef(node_name), TierkreisNode.from_proto(pg_node), {}
            )

            # hack for mainting fresh names
            if "_" in node_name:
                base, count = node_name.split("_", 2)
                if base in tk_graph._name_counts:
                    try:
                        count = int(count)
                        tk_graph._name_counts[base] = count + 1
                    except ValueError:
                        pass

        for pg_edge in pg_graph.edges:
            source_node = NodeRef(pg_edge.node_from)
            target_node = NodeRef(pg_edge.node_to)
            source = NodePort(source_node, PortID(pg_edge.port_from))
            target = NodePort(target_node, PortID(pg_edge.port_to))
            edge_type = TierkreisType.from_proto(pg_edge.edge_type)

            tk_graph.add_edge(source, target, edge_type)
        return tk_graph

    def to_python(self, type_: typing.Type[T]) -> T:
        if isinstance(type_, typing.TypeVar) or type_ is TierkreisGraph:
            return cast(T, self)
        raise TypeError()


def _get_edge(
    edge_type: Optional[Union[Type, TierkreisType]]
) -> Optional[TierkreisType]:
    if edge_type is None:
        return None
    else:
        return (
            edge_type
            if isinstance(edge_type, TierkreisType)
            else TierkreisType.from_python(edge_type)
        )


def tierkreis_graphviz(tk_graph: TierkreisGraph) -> gv.Digraph:
    """
    Return a visual representation of the TierkreisGraph as a graphviz object.

    :returns:   Representation of the TierkreisGraph
    :rtype:     graphviz.DiGraph
    """
    gv_graph = gv.Digraph(
        "TierKreis",
        strict=True,
    )

    gv_graph.attr(rankdir="LR", ranksep="0.3", nodesep="0.15", margin="0")
    wire_color = "red"
    task_color = "darkolivegreen3"
    io_color = "green"
    out_color = "black"
    in_color = "white"

    boundary_node_attr = {"fontname": "Courier", "fontsize": "8"}
    boundary_nodes = {tk_graph.input_node_name, tk_graph.output_node_name}

    with gv_graph.subgraph(name="cluster_input") as cluster:
        cluster.attr(rank="source")
        cluster.node_attr.update(shape="point", color=io_color)
        for port in tk_graph.inputs():
            cluster.node(
                name=f"({tk_graph.input_node_name}out, {port})",
                xlabel=f"{port}",
                **boundary_node_attr,
            )

    with gv_graph.subgraph(name="cluster_output") as cluster:
        cluster.attr(rank="sink")
        cluster.node_attr.update(shape="point", color=io_color)
        for port in tk_graph.outputs():
            cluster.node(
                name=f"({tk_graph.output_node_name}in, {port})",
                xlabel=f"{port}",
                **boundary_node_attr,
            )

    node_cluster_attr = {
        "style": "rounded, filled",
        "color": task_color,
        "fontname": "Times-Roman",
        "fontsize": "10",
        "margin": "5",
        "lheight": "100",
    }
    in_port_node_attr = {
        "color": in_color,
        "shape": "point",
        "weight": "2",
        "fontname": "Helvetica",
        "fontsize": "8",
        "rank": "source",
    }
    out_port_node_attr = {
        "color": out_color,
        "shape": "point",
        "weight": "2",
        "fontname": "Helvetica",
        "fontsize": "8",
        "rank": "sink",
    }
    count = 0

    for node_name in tk_graph.nodes():

        if node_name not in boundary_nodes:
            with gv_graph.subgraph(name=f"cluster_{node_name}{count}") as cluster:
                count = count + 1
                cluster.attr(label=node_name, **node_cluster_attr)

                incoming_edges = tk_graph.in_edges(node_name)

                for edge in incoming_edges:
                    cluster.node(
                        name=f"({node_name}in, {edge.target.port})",
                        xlabel=f"{edge.target.port}",
                        **in_port_node_attr,
                    )

                outgoing_edges = tk_graph.out_edges(node_name)

                for edge in outgoing_edges:
                    cluster.node(
                        name=f"({node_name}out, {edge.source.port})",
                        xlabel=f"{edge.source.port}",
                        **out_port_node_attr,
                    )

    edge_attr = {
        "weight": "2",
        "arrowhead": "vee",
        "arrowsize": "0.2",
        "headclip": "true",
        "tailclip": "true",
    }
    print(list(gv_graph))
    for edge in tk_graph.edges():
        src_nodename = f"({edge.source.node_ref.name}out, {edge.source.port})"
        tgt_nodename = f"({edge.target.node_ref.name}in, {edge.target.port})"
        print("edge", src_nodename, tgt_nodename)

        gv_graph.edge(src_nodename, tgt_nodename, color=wire_color, **edge_attr)

    return gv_graph


# GraphValue defined after TierkreisGraph to avoid circular/delayed import


@dataclass(frozen=True)
class GraphValue(TierkreisValue):
    value: TierkreisGraph
    _proto_name: str = "graph"
    _pytype: typing.Type = TierkreisGraph

    def to_proto(self) -> pg.Value:
        return pg.Value(graph=self.value.to_proto())

    def to_python(self, type_: typing.Type[T]) -> T:
        from tierkreis.core.python import RuntimeGraph

        if isinstance(type_, typing.TypeVar):
            return cast(T, self)
        if typing.get_origin(type_) is RuntimeGraph:
            return cast(T, self.value)
        if issubclass(type_, TierkreisGraph):
            return cast(T, self.value)
        raise TypeError()

    @classmethod
    def from_python(cls, value: Any) -> "TierkreisValue":
        return cls(value)

    @classmethod
    def from_proto(cls, value: Any) -> "TierkreisValue":
        return cls(TierkreisGraph.from_proto(cast(pg.Graph, value)))
