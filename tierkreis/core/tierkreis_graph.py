# pylint: disable=wrong-import-position, wrong-import-order
"""Utilities for building tierkreis graphs."""
import copy
import typing
from abc import ABC, abstractmethod
from dataclasses import dataclass
from itertools import count, dropwhile
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple, Type, Union, cast

import betterproto
import networkx as nx  # type: ignore
from networkx.classes.reportviews import (  # type: ignore
    InMultiEdgeDataView,
    OutMultiEdgeDataView,
)
import tierkreis.core.protos.tierkreis.graph as pg
from tierkreis.core.function import TierkreisFunction
from tierkreis.core.types import TierkreisType
from tierkreis.core.values import T, TierkreisValue

FunctionID = str
PortID = str


class TierkreisNode(ABC):
    @abstractmethod
    def to_proto(self) -> pg.Node:
        pass

    @classmethod
    def from_proto(cls, node: pg.Node) -> "TierkreisNode":
        name, out_node = betterproto.which_one_of(node, "node")

        result: TierkreisNode
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
        elif name == "tag":
            result = TagNode(cast(str, out_node))
        elif name == "match":
            result = MatchNode()
        else:
            raise ValueError(f"Unknown protobuf node type: {name}")

        if not isinstance(result, cls):
            raise TypeError()

        return result

    def is_discard_node(self) -> bool:
        """Delete nodes have some special behaviour, check for it."""
        return getattr(self, "function_name", "") == "builtin/discard"


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


@dataclass
class TagNode(TierkreisNode):
    tag_name: str

    def to_proto(self) -> pg.Node:
        return pg.Node(tag=self.tag_name)


@dataclass
class MatchNode(TierkreisNode):
    def to_proto(self) -> pg.Node:
        return pg.Node(match=pg.Empty())


@dataclass
class NodeRef:
    name: str

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, NodeRef):
            return False
        return self.name == o.name

    def __getitem__(self, key: str) -> "NodePort":
        # syntactic sugar for creating references to output ports from node
        return NodePort(self, key)


@dataclass(frozen=True)
class NodePort:
    node_ref: NodeRef
    port: PortID


@dataclass
class TierkreisEdge:
    source: NodePort
    target: NodePort
    type_: Optional[TierkreisType]

    def to_proto(self) -> pg.Edge:
        edge_type = None if self.type_ is None else self.type_.to_proto()
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

    @dataclass
    class MissingEdge(Exception):
        source: NodePort
        target: NodePort

    def __init__(self, name: Optional[str] = None) -> None:
        self.name = name
        self._graph = nx.MultiDiGraph()
        self.input = self.add_node(InputNode(), self.input_node_name)
        self.output = self.add_node(OutputNode(), self.output_node_name)

    def inputs(self) -> List[str]:
        return [edge.source.port for edge in self.out_edges(self.input)]

    def outputs(self) -> List[str]:
        return [edge.target.port for edge in self.in_edges(self.output)]

    @property
    def n_nodes(self) -> int:
        return len(self._graph)

    def _get_fresh_name(self) -> str:
        return next(
            dropwhile(
                lambda name: name in self._graph,
                map(lambda i: f"NewNode({i})", count(0)),
            )
        )

    def _to_nodeport(self, source: Union[NodePort, NodeRef, Any]) -> NodePort:
        if not isinstance(source, (NodePort, NodeRef)):
            try:
                source = self.add_const(source)
            except ValueError as err:
                raise ValueError(
                    "Incoming wire must be a NodePort, "
                    "a NodeRef to a node with a single output 'value', "
                    "or a constant value to be added as a ConstNode."
                ) from err
        return source if isinstance(source, NodePort) else source["value"]

    def add_node(
        self,
        _tk_node: TierkreisNode,
        _tk_node_name: Optional[str] = None,
        /,
        **incoming_wires: IncomingWireType,
    ) -> NodeRef:
        if _tk_node_name is None:
            _tk_node_name = self._get_fresh_name()
        node_ref = NodeRef(_tk_node_name)

        if node_ref.name in self._graph.nodes:
            raise self.DuplicateNodeName(node_ref.name)

        self._graph.add_node(node_ref.name, node_info=_tk_node)
        for target_port_name, source in incoming_wires.items():
            self.add_edge(self._to_nodeport(source), node_ref[target_port_name])

        return node_ref

    def add_func(
        self,
        _tk_function: Union[str, TierkreisFunction],
        _tk_node_name: Optional[str] = None,
        /,
        **kwargs: IncomingWireType,
    ) -> NodeRef:
        f_name = (
            _tk_function.name
            if isinstance(_tk_function, TierkreisFunction)
            else _tk_function
        )

        return self.add_node(FunctionNode(f_name), _tk_node_name, **kwargs)

    def add_const(self, value: Any, name: Optional[str] = None) -> NodeRef:
        tkval = (
            value
            if isinstance(value, TierkreisValue)
            else TierkreisValue.from_python(value)
        )

        return self.add_node(ConstNode(tkval), name)

    def add_box(
        self,
        graph: "TierkreisGraph",
        name: Optional[str] = None,
        /,
        **kwargs: IncomingWireType,
    ) -> NodeRef:
        # TODO restrict to graph i/o
        return self.add_node(BoxNode(graph), name, **kwargs)

    def add_match(
        self,
        variant_value: IncomingWireType,
        _tk_node_name: Optional[str] = None,
        /,
        **variant_handlers: IncomingWireType,
    ) -> NodeRef:
        return self.add_node(
            MatchNode(), _tk_node_name, variant_value=variant_value, **variant_handlers
        )

    def add_tag(
        self,
        tag: str,
        *,  # Following are keyword only
        name: Optional[str] = None,
        value: IncomingWireType,
    ) -> NodeRef:
        return self.add_node(TagNode(tag), name, value=value)

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
            node_ref = self.add_node(node, new_node_name, **input_ports)
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
                NodeRef(source_node)[edge.source.port],
                NodeRef(target_node)[edge.target.port],
                edge.type_,
            )

        return return_outputs

    def _inline_box(self, box_node_name: str, recursive: bool) -> None:
        """Replace a box node with the graph it contains, inplace. Optionally
        use the recursive flag to inline all boxes inside the box
        recursively."""

        node = self[box_node_name]
        assert isinstance(node, BoxNode)
        boxed_g = node.graph
        if recursive:
            boxed_g = boxed_g.inline_boxes(recursive)

        curr_inputs = cast(
            InMultiEdgeDataView,
            self._graph.in_edges(box_node_name, data="edge_info", keys=True),
        )

        incoming_ports = {
            edge.target.port: edge.source for (_, _, _, edge) in curr_inputs
        }

        inserted_outputs = self.insert_graph(boxed_g, box_node_name, **incoming_ports)
        curr_outputs = cast(
            OutMultiEdgeDataView,
            self._graph.out_edges(box_node_name, data="edge_info", keys=True),
        )
        edge_bin = []
        for (source, target, key, edge) in curr_outputs:
            edge = cast(TierkreisEdge, edge)
            edge_bin.append((source, target, key))
            self.add_edge(inserted_outputs[edge.source.port], edge.target, edge.type_)

        for edge in edge_bin:
            self._graph.remove_edge(*edge)

    def inline_boxes(self, recursive=False) -> "TierkreisGraph":
        """Inline boxes by inserting the graphs they contain in to the parent
        graph. Optionally do this recursively.

        :return: Inlined graph
        :rtype: TierkreisGraph
        """

        graph = copy.deepcopy(self)
        node_bin: Set[str] = set()
        for node_name, node in graph.nodes().items():

            if not isinstance(node, BoxNode):
                continue

            graph._inline_box(node_name, recursive)

            node_bin.add(node_name)

        for node_name in node_bin:
            graph._graph.remove_node(node_name)

        return graph

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
        tk_type = _to_tierkreis_type(edge_type)

        edge = TierkreisEdge(node_port_from, node_port_to, tk_type)
        # if port is currently connected to discard, replace that edge
        try:
            del_edge = next(
                out_edge
                for out_edge in self.out_edges(edge.source.node_ref)
                if out_edge.source.port == edge.source.port
                and self[out_edge.target.node_ref].is_discard_node()
            )
            self._graph.remove_edge(
                del_edge.source.node_ref.name, del_edge.target.node_ref.name
            )
            self._graph.remove_node(del_edge.target.node_ref.name)
        except StopIteration:
            pass
        self._graph.add_edge(
            node_port_from.node_ref.name,
            node_port_to.node_ref.name,
            edge_info=edge,
        )
        return edge

    def annotate_input(
        self, input_port: str, edge_type: Optional[Union[Type, TierkreisType]]
    ):
        (in_edge,) = [
            e
            for e in self.out_edges(self.input_node_name)
            if e.source.port == input_port
        ]
        tk_type = _to_tierkreis_type(edge_type)
        in_edge.type_ = tk_type

    def annotate_output(
        self, output_port: str, edge_type: Optional[Union[Type, TierkreisType]]
    ):
        (out_edge,) = [
            e
            for e in self.in_edges(self.output_node_name)
            if e.target.port == output_port
        ]
        tk_type = _to_tierkreis_type(edge_type)
        out_edge.type_ = tk_type

    def get_edge(self, source: NodePort, target: NodePort) -> TierkreisEdge:
        all_edges = (
            edge_data["edge_info"]
            for edge_data in cast(
                Dict[int, Dict[str, TierkreisEdge]],
                self._graph.get_edge_data(source.node_ref.name, target.node_ref.name),
            ).values()
        )
        try:
            return next(
                dropwhile(
                    lambda edge: not (edge.source == source and edge.target == target),
                    all_edges,
                )
            )
        except StopIteration as e:
            raise self.MissingEdge(source, target) from e

    def set_outputs(self, **kwargs: Union[NodePort, NodeRef, Any]) -> None:
        for out_name, port in kwargs.items():
            self.add_edge(self._to_nodeport(port), self.output[out_name])

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

    def discard(self, out_port: NodePort) -> None:
        _ = self.add_func("builtin/discard", value=out_port)

    def make_pair(
        self, first_port: IncomingWireType, second_port: IncomingWireType
    ) -> NodePort:
        make_n = self.add_func(
            "builtin/make_pair", first=first_port, second=second_port
        )
        return make_n["pair"]

    def unpack_pair(self, pair_port: IncomingWireType) -> Tuple[NodePort, NodePort]:
        unp_n = self.add_func("builtin/unpack_pair", pair=pair_port)
        return unp_n["first"], unp_n["second"]

    def make_vec(self, element_ports: List[IncomingWireType]) -> NodePort:
        vec_port = self.add_const(list())["value"]

        for port in element_ports:
            vec_port = self.add_func("builtin/push", vec=vec_port, item=port)["vec"]

        return vec_port

    def vec_last_n_elems(self, vec_port: NodePort, n_elements: int) -> List[NodePort]:
        curr_arr = vec_port
        outports: List[NodePort] = []
        for _ in range(n_elements):
            pop = self.add_func("builtin/pop", vec=curr_arr)
            curr_arr = pop["vec"]
            outports.insert(0, pop["item"])
        return outports

    def copy_value(self, value: IncomingWireType) -> Tuple[NodePort, NodePort]:
        copy_n = self.add_func("builtin/copy", value=value)

        return copy_n["value_0"], copy_n["value_1"]

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
        for node_name, pg_node in pg_graph.nodes.items():
            if node_name in {tk_graph.input_node_name, tk_graph.output_node_name}:
                continue
            tk_graph.add_node(TierkreisNode.from_proto(pg_node), node_name)

        for pg_edge in pg_graph.edges:
            source_node = NodeRef(pg_edge.node_from)
            target_node = NodeRef(pg_edge.node_to)
            source = NodePort(source_node, PortID(pg_edge.port_from))
            target = NodePort(target_node, PortID(pg_edge.port_to))
            # TODO make all edge type conversions possible
            edge_type = pg_edge.edge_type
            tk_edge_type: Optional[TierkreisType] = None
            if edge_type is not None:
                try:
                    tk_edge_type = TierkreisType.from_proto(edge_type)
                except ValueError:
                    tk_edge_type = None

            tk_graph.add_edge(source, target, tk_edge_type)
        return tk_graph

    def to_python(self, type_: typing.Type[T]) -> T:
        if isinstance(type_, typing.TypeVar) or type_ is TierkreisGraph:
            return cast(T, self)
        raise TypeError()


def _to_tierkreis_type(
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
    _class_pytype: typing.ClassVar[typing.Type] = TierkreisGraph

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

    def __str__(self) -> str:
        return "GraphValue"

    def to_tksl(self) -> str:
        return "Graph"


# allow graph displays in jupyter notebooks
from tierkreis.core.graphviz import tierkreis_to_graphviz


setattr(
    TierkreisGraph,
    "_repr_svg_",
    lambda self: tierkreis_to_graphviz(  # pylint: disable=protected-access
        self
    )._repr_svg_(),
)
