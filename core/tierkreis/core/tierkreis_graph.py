"""Utilities for building tierkreis graphs."""
import typing
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple, Type, Union, cast

import betterproto
import networkx as nx  # type: ignore
import tierkreis.core.protos.tierkreis.graph as pg
from tierkreis.core.types import TierkreisType
from tierkreis.core.values import T, TierkreisValue
from tierkreis.core.function import TierkreisFunction

FunctionID = str
PortID = str


@dataclass
class TierkreisNode(ABC):
    @abstractmethod
    def to_proto(self) -> pg.Node:
        pass

    @classmethod
    def from_proto(cls, node: pg.Node) -> "TierkreisNode":
        name, out_node = betterproto.which_one_of(node, "node")

        if name == "const":
            result = ConstNode(TierkreisValue.from_proto(cast(pg.Value, out_node)))
        elif name == "box":
            result = BoxNode(TierkreisGraph.from_proto(cast(pg.Graph, out_node)))
        elif name == "function":
            result = FunctionNode(cast(FunctionID, out_node))
        elif name == "input":
            result = InputNode()
        elif name == "output":
            result = OutputNode()
        else:
            raise ValueError(f"Unknown protobuf node type: {name}")

        if not isinstance(result, cls):
            raise TypeError()

        return result


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

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, NodeRef):
            return False
        return self.name == o.name


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


# allow specifying input as a port, node with single output, or constant value
IncomingWireType = Union[NodePort, NodeRef, Any]


class TierkreisGraph:
    """TierkreisGraph."""

    input_node_name: str = "input"
    output_node_name: str = "output"

    @dataclass
    class DuplicateNodeName(Exception):
        name: str

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
        incoming_wires: Dict[str, IncomingWireType],
    ) -> NodeRef:
        if node_ref.name in self._graph.nodes:
            raise self.DuplicateNodeName(node_ref.name)

        self._graph.add_node(node_ref.name, node_info=node)
        for target_port_name, source in incoming_wires.items():
            target = NodePort(node_ref, target_port_name)
            if not isinstance(source, (NodePort, NodeRef)):
                try:
                    source = self.add_const(source)
                except ValueError as err:
                    raise ValueError(
                        "Incoming wire must be a NodePort, "
                        "a NodeRef to a node with a single output 'value', "
                        "or a constant value to be added as a ConstNode."
                    ) from err

            source = source if isinstance(source, NodePort) else source.out.value
            self.add_edge(source, target)

        return node_ref

    def add_node(
        self,
        _tk_function: Union[str, TierkreisFunction],
        _tk_node_name: Optional[str] = None,
        /,
        **kwargs: IncomingWireType,
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
        /,
        **kwargs: IncomingWireType,
    ) -> NodeRef:
        # TODO restrict to graph i/o
        if name is None:
            name = self._get_fresh_name("box")
        return self._add_node(NodeRef(name, set(), False), BoxNode(graph), kwargs)

    def insert_graph(
        self,
        graph: "TierkreisGraph",
        name_prefix: str = "",
        /,
        **kwargs: IncomingWireType,
    ) -> Dict[str, NodePort]:

        # gather maps from I/O name to node ports
        input_wires = {
            e.source.port: (e.target.node_ref.name, e.target.port)
            for e in graph.out_edges(graph.input_node_name)
        }
        output_wires = {
            e.target.port: (e.source.node_ref.name, e.source.port)
            for e in graph.in_edges(graph.output_node_name)
        }

        # return a map from subgraph outputs to inserted nodeports
        return_outputs: Dict[str, NodePort] = dict()
        node_refs = dict()
        for node_name, node in graph.nodes().items():
            if node_name in {graph.input_node_name, graph.output_node_name}:
                continue

            # find any provided incoming wires to wire to this node
            input_ports = {
                input_port: kwargs[graph_input]
                for graph_input, (
                    input_node,
                    input_port,
                ) in input_wires.items()
                if input_node == node_name and graph_input in kwargs
            }

            new_node_name = name_prefix + node_name
            if new_node_name in self._graph.nodes:
                raise self.DuplicateNodeName(new_node_name)

            # find any node ports that are graph outputs
            output_ports = {
                graph_output: output_port
                for graph_output, (
                    output_node,
                    output_port,
                ) in output_wires.items()
                if output_node == node_name
            }
            node_ref = self._add_node(
                NodeRef(new_node_name, set(output_ports.values())), node, input_ports
            )
            node_refs[new_node_name] = node_ref
            return_outputs.update(
                {
                    graph_output: NodePort(node_ref, output_port)
                    for graph_output, output_port in output_ports.items()
                }
            )

        for edge in graph.edges():
            source_node = edge.source.node_ref.name
            target_node = edge.target.node_ref.name
            if (
                source_node == graph.input_node_name
                or target_node == graph.output_node_name
            ):
                continue
            source_node = name_prefix + source_node
            target_node = name_prefix + target_node

            self.add_edge(
                NodePort(node_refs[source_node], edge.source.port),
                NodePort(node_refs[target_node], edge.target.port),
                edge.type,
            )

        return return_outputs

    def delete(self, out_port: NodePort) -> None:
        _ = self.add_node("builtin/delete", value=out_port)

    def make_pair(
        self, first_port: IncomingWireType, second_port: IncomingWireType
    ) -> NodePort:
        make_n = self.add_node(
            "builtin/make_pair", first=first_port, second=second_port
        )
        return make_n.out.pair

    def unpack_pair(self, pair_port: IncomingWireType) -> Tuple[NodePort, NodePort]:
        unp_n = self.add_node("builtin/unpack_pair", pair=pair_port)
        return unp_n.out.first, unp_n.out.second

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
            if node_name in {tk_graph.input_node_name, tk_graph.output_node_name}:
                continue
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
            # TODO make all edge type conversions possible
            edge_type = pg_edge.edge_type
            if edge_type is not None:
                try:
                    edge_type = TierkreisType.from_proto(edge_type)
                except ValueError:
                    edge_type = None

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
            return cast(T, RuntimeGraph(self.value))
        if issubclass(type_, TierkreisGraph):
            return cast(T, self.value)
        raise TypeError()

    @classmethod
    def from_python(cls, value: Any) -> "TierkreisValue":
        return cls(value)

    @classmethod
    def from_proto(cls, value: Any) -> "TierkreisValue":
        return cls(TierkreisGraph.from_proto(cast(pg.Graph, value)))
