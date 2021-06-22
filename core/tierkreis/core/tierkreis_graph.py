"""Utilities for building tierkreis graphs."""
import typing
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import (
    Any,
    Dict,
    Iterator,
    List,
    NewType,
    Optional,
    Tuple,
    Type,
    Union,
    cast,
)

import types
import betterproto
import graphviz as gv  # type: ignore
import networkx as nx  # type: ignore
import tierkreis.core.protos.tierkreis.graph as pg
from tierkreis.core.types import (
    GraphType,
    TierkreisType,
    TypeScheme,
    Row,
)
from tierkreis.core.values import T, TierkreisValue

FunctionID = str
PortID = NewType("PortID", str)


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
    def type_scheme(self) -> TypeScheme:
        pass

    @abstractmethod
    def inputs(self) -> Dict[str, TierkreisType]:
        pass

    @abstractmethod
    def outputs(self) -> Dict[str, TierkreisType]:
        pass

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
        else:
            raise ValueError(f"Unknown protobuf node type: {name}")


@dataclass
class InputNode(TierkreisNode):
    _inputs: Dict[str, TierkreisType] = field(default_factory=dict)

    def type_scheme(self) -> TypeScheme:
        return TypeScheme(
            {}, [], GraphType(inputs=Row(), outputs=Row(content=self._inputs))
        )

    def inputs(self) -> Dict[str, TierkreisType]:
        return dict()

    def outputs(self) -> Dict[str, TierkreisType]:
        return self._inputs

    def to_proto(self) -> pg.Node:
        return pg.Node(input=pg.Empty())

    def set_input(self, name: str, edge_type: TierkreisType) -> None:
        self._inputs[name] = edge_type


@dataclass
class OutputNode(TierkreisNode):
    _outputs: Dict[str, TierkreisType] = field(default_factory=dict)

    def type_scheme(self) -> TypeScheme:
        return TypeScheme(
            {}, [], GraphType(outputs=Row(), inputs=Row(content=self._outputs))
        )

    def inputs(self) -> Dict[str, TierkreisType]:
        return self._outputs

    def outputs(self) -> Dict[str, TierkreisType]:
        return dict()

    def to_proto(self) -> pg.Node:
        return pg.Node(output=pg.Empty())

    def set_output(self, name: str, edge_type: TierkreisType) -> None:
        self._outputs[name] = edge_type


@dataclass
class ConstNode(TierkreisNode):
    value: TierkreisValue

    def type_scheme(self) -> TypeScheme:
        # TODO return "unknown type"

        return TypeScheme(
            {},
            [],
            GraphType(outputs=Row(content={"value": NotImplemented}), inputs=Row()),
        )

    def inputs(self) -> Dict[str, TierkreisType]:
        return dict()

    def outputs(self) -> Dict[str, TierkreisType]:
        # TODO return "unknown type"
        return {"value": NotImplemented}

    def to_proto(self) -> pg.Node:
        return pg.Node(const=self.value.to_proto())


@dataclass
class BoxNode(TierkreisNode):
    graph: "TierkreisGraph"

    def type_scheme(self) -> TypeScheme:
        return TypeScheme(
            {},
            [],
            GraphType(
                outputs=Row(content=self.graph.outputs),
                inputs=Row(content=self.graph.inputs),
            ),
        )

    def inputs(self) -> Dict[str, TierkreisType]:
        return self.graph.inputs

    def outputs(self) -> Dict[str, TierkreisType]:
        return self.graph.outputs

    def to_proto(self) -> pg.Node:
        return pg.Node(box=self.graph.to_proto())


@dataclass
class FunctionNode(TierkreisNode):
    function_name: str
    _function: Optional[TierkreisFunction] = None

    def type_scheme(self) -> TypeScheme:
        if self._function is None:
            raise RuntimeError("Function node has no loaded type signature.")
        return self._function.type_scheme

    def inputs(self) -> Dict[str, TierkreisType]:
        if self._function is None:
            raise RuntimeError("Function node has no loaded type signature.")
        return self._function.type_scheme.body.inputs.content

    def outputs(self) -> Dict[str, TierkreisType]:
        if self._function is None:
            raise RuntimeError("Function node has no loaded type signature.")
        return self._function.type_scheme.body.outputs.content

    def to_proto(self) -> pg.Node:
        return pg.Node(function=self.function_name)


@dataclass(frozen=True)
class NodeRef:
    name: str
    node: TierkreisNode

    @dataclass
    class Ports:
        class PortNotFound(Exception):
            pass

        _node_ref: "NodeRef"
        _ports: Dict[str, TierkreisType]
        _check_name: bool = True

        def __getattribute__(self, name: str) -> "NodePort":
            if name in super().__getattribute__(
                "_ports"
            ) or not super().__getattribute__("_check_name"):
                return NodePort(super().__getattribute__("_node_ref"), PortID(name))
            raise super().__getattribute__("PortNotFound")(name)

    @property
    def in_port(self) -> "NodeRef.Ports":
        scheme = self.node.type_scheme()
        check_port = scheme.body.inputs.rest is None
        return self.Ports(self, scheme.body.inputs.content, check_port)

    @property
    def out_port(self) -> "NodeRef.Ports":
        scheme = self.node.type_scheme()
        check_port = scheme.body.inputs.rest is None
        return self.Ports(self, scheme.body.outputs.content, check_port)


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

        self._name_counts = {name: 0 for name in ("const, box")}

        self._functions: Dict[str, Dict[str, TierkreisFunction]] = dict()

    @property
    def n_nodes(self) -> int:
        return len(self._graph)

    @property
    def inputs(self) -> Dict[str, TierkreisType]:
        return self[self.input_node_name].node.outputs()

    @property
    def outputs(self) -> Dict[str, TierkreisType]:
        return self[self.output_node_name].node.inputs()

    def _get_fresh_name(self, name_class: str) -> str:
        if name_class not in self._name_counts:
            self._name_counts[name_class] = 0
        count = self._name_counts[name_class]
        suffix = f"_{count}" if count > 0 else ""

        self._name_counts[name_class] += 1
        return f"{name_class}{suffix}"

    def _add_node(self, name: str, node: TierkreisNode) -> NodeRef:
        self._graph.add_node(name, node_info=node)
        return NodeRef(name, node)

    def add_function_node(
        self,
        function: Union[str, TierkreisFunction],
        name: Optional[str] = None,
    ) -> NodeRef:
        f_name = function if isinstance(function, str) else function.name
        if name is None:
            name = self._get_fresh_name(f_name)
        if isinstance(function, TierkreisFunction):
            _function = function
        else:
            _function = self._find_sig(function)
        return self._add_node(name, FunctionNode(f_name, _function=_function))

    def _find_sig(self, name: str) -> Optional[TierkreisFunction]:
        namespace, f_name = name.split("/", 2)

        if namespace in self._functions and f_name in self._functions[namespace]:
            return self._functions[namespace][f_name]
        return None

    def load_signature(self, signature_module: types.ModuleType) -> None:
        def name_pairs(mod: types.ModuleType) -> Iterator[Tuple[str, Any]]:
            return ((k, v) for k, v in vars(mod).items() if not k.startswith("__"))

        self._functions = {
            namespace: {f_name: func for f_name, func in name_pairs(mod)}
            for namespace, mod in name_pairs(signature_module)
        }

        for node in self.nodes().values():
            if isinstance(node, FunctionNode):
                node._function = self._find_sig(node.function_name)

    def add_const(self, value: Any, name: Optional[str] = None) -> NodeRef:
        if name is None:
            name = self._get_fresh_name("const")
        tkval = (
            value
            if isinstance(value, TierkreisValue)
            else TierkreisValue.from_python(value)
        )
        return self._add_node(name, ConstNode(tkval))

    def add_box(self, graph: "TierkreisGraph", name: Optional[str] = None) -> NodeRef:
        if name is None:
            name = self._get_fresh_name("box")
        return self._add_node(name, BoxNode(graph))

    def nodes(self) -> Dict[str, TierkreisNode]:
        return {
            name: self._graph.nodes[name]["node_info"] for name in self._graph.nodes
        }

    def edges(self) -> List[TierkreisEdge]:
        return [
            cast(TierkreisEdge, edge_info[2])
            for edge_info in self._graph.edges(data="edge_info", keys=False)
        ]

    def __getitem__(self, key: Union[str, NodeRef]) -> NodeRef:
        if isinstance(key, NodeRef):
            if not self._graph.has_node(key.name):
                raise KeyError(f"Graph does not contain node with name {key.name}")
            return key
        return NodeRef(key, self._graph.nodes[key]["node_info"])

    def add_edge(
        self,
        node_port_from: NodePort,
        node_port_to: NodePort,
        edge_type: Optional[Union[Type, TierkreisType]] = None,
    ) -> TierkreisEdge:
        if edge_type is None:
            tk_type = None
        else:
            tk_type = (
                edge_type
                if isinstance(edge_type, TierkreisType)
                else TierkreisType.from_python(edge_type)
            )

        edge = TierkreisEdge(node_port_from, node_port_to, tk_type)

        self._graph.add_edge(
            node_port_from.node_ref.name,
            node_port_to.node_ref.name,
            edge_info=edge,
        )
        return edge

    def register_input(
        self, name: str, node_port: NodePort, edge_type: Optional[Type] = None
    ):
        node = cast(InputNode, self[self.input_node_name].node)
        if edge_type is None:
            tk_type = node_port.node_ref.node.inputs()[node_port.port]
            # TODO check if tk_type is valid or unknown (e.g. ConstNode)
        else:
            tk_type = edge_type
        node.set_input(name, tk_type)

        self.add_edge(NodePort(self[self.input_node_name], PortID(name)), node_port)

    def register_output(
        self, name: str, node_port: NodePort, edge_type: Optional[Type] = None
    ):
        node = cast(OutputNode, self[self.output_node_name].node)
        if edge_type is None:
            tk_type = node_port.node_ref.node.outputs()[node_port.port]
            # TODO check if tk_type is valid or unknown
        else:
            tk_type = edge_type
        node.set_output(name, tk_type)
        self.add_edge(node_port, NodePort(self[self.output_node_name], PortID(name)))

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

    def to_proto(self) -> pg.Graph:
        pg_graph = pg.Graph()
        pg_graph.nodes = {
            node_name: self[node_name].node.to_proto()
            for node_name in cast(Iterator[str], self._graph.nodes)
        }
        pg_graph.edges = [
            cast(TierkreisEdge, edge_info[2]).to_proto()
            for edge_info in self._graph.edges(data="edge_info", keys=False)
        ]
        return pg_graph

    @staticmethod
    def from_proto(pg_graph: pg.Graph) -> "TierkreisGraph":
        tk_graph = TierkreisGraph()
        for node_name, pg_node in pg_graph.nodes.items():
            tk_graph._add_node(node_name, TierkreisNode.from_proto(pg_node))
        for pg_edge in pg_graph.edges:
            source_node = tk_graph[pg_edge.node_from]
            target_node = tk_graph[pg_edge.node_to]
            source = NodePort(source_node, PortID(pg_edge.port_from))
            target = NodePort(target_node, PortID(pg_edge.port_to))
            tk_graph.add_edge(
                source, target, TierkreisType.from_proto(pg_edge.edge_type)
            )
        return tk_graph

    def to_python(self, type_: typing.Type[T]) -> T:
        if isinstance(type_, typing.TypeVar) or type_ is TierkreisGraph:
            return cast(T, self)
        raise TypeError()


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
        for port in tk_graph.inputs:
            cluster.node(
                name=f"({tk_graph.input_node_name}out, {port})",
                xlabel=f"{port}",
                **boundary_node_attr,
            )

    with gv_graph.subgraph(name="cluster_output") as cluster:
        cluster.attr(rank="sink")
        cluster.node_attr.update(shape="point", color=io_color)
        for port in tk_graph.outputs:
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
        else:
            raise TypeError()

    @classmethod
    def from_python(cls, value: Any) -> "TierkreisValue":
        return cls(value)

    @classmethod
    def from_proto(cls, value: Any) -> "TierkreisValue":
        return cls(TierkreisGraph.from_proto(cast(pg.Graph, value)))
