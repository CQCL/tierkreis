"""Utilities for building tierkreis graphs."""
import copy
import typing
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Iterable,
    Iterator,
    List,
    Mapping,
    Optional,
    Tuple,
    Type,
    Union,
    cast,
)

import betterproto
import networkx as nx

import tierkreis.core.protos.tierkreis.v1alpha1.graph as pg
from tierkreis.core.function import FunctionName
from tierkreis.core.types import TierkreisType
from tierkreis.core.values import T, TierkreisValue

if TYPE_CHECKING:
    from tierkreis.builder import Unpack, ValueSource

PortID = str
Location = pg.Location


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
            box_node = cast(pg.BoxNode, out_node)
            result = BoxNode(
                graph=TierkreisGraph.from_proto(box_node.graph), location=box_node.loc
            )
        elif name == "function":
            fn_node = cast(pg.FunctionNode, out_node)
            result = FunctionNode(
                FunctionName.from_proto(fn_node.name), fn_node.retry_secs
            )
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
        return False

    def is_copy_node(self) -> bool:
        return False

    def is_unpack_node(self) -> bool:
        return False


@dataclass(frozen=True)
class InputNode(TierkreisNode):
    def to_proto(self) -> pg.Node:
        return pg.Node(input=pg.Empty())


@dataclass(frozen=True)
class OutputNode(TierkreisNode):
    def to_proto(self) -> pg.Node:
        return pg.Node(output=pg.Empty())


@dataclass(frozen=True)
class ConstNode(TierkreisNode):
    value: TierkreisValue

    def to_proto(self) -> pg.Node:
        return pg.Node(const=self.value.to_proto())


@dataclass(frozen=True)
class BoxNode(TierkreisNode):
    graph: "TierkreisGraph"
    location: Location

    def to_proto(self) -> pg.Node:
        return pg.Node(box=pg.BoxNode(loc=self.location, graph=self.graph.to_proto()))


@dataclass(frozen=True)
class FunctionNode(TierkreisNode):
    function_name: FunctionName
    retry_secs: Optional[int] = None  # Stored as uint32, so always >=0

    def to_proto(self) -> pg.Node:
        return pg.Node(
            function=pg.FunctionNode(
                name=self.function_name.to_proto(), retry_secs=self.retry_secs
            )
        )

    def is_discard_node(self) -> bool:
        return self.function_name == FunctionName("discard")

    def is_copy_node(self) -> bool:
        return self.function_name == FunctionName("copy")

    def is_unpack_node(self) -> bool:
        return self.function_name == FunctionName("unpack_struct")


@dataclass(frozen=True)
class TagNode(TierkreisNode):
    tag_name: str

    def to_proto(self) -> pg.Node:
        return pg.Node(tag=self.tag_name)


@dataclass(frozen=True)
class MatchNode(TierkreisNode):
    def to_proto(self) -> pg.Node:
        return pg.Node(match=pg.Empty())


@dataclass(frozen=True)
class NodeRef(Iterable):
    idx: int
    graph: "TierkreisGraph"
    outports: Optional[list[str]] = field(default=None, compare=False)

    def with_retry_secs(self, retry_secs: int) -> "NodeRef":
        """If this NodeRef refers to a FunctionNode, set its retry time in seconds.
        Otherwise, raises ValueError."""
        node = self.graph[self.idx]
        if not isinstance(node, FunctionNode):
            raise ValueError(
                "{self} must refer to a FunctionNode, but actually refers to {node}"
            )
        self.graph[self.idx] = FunctionNode(node.function_name, retry_secs)
        return self

    def default_nodeport(self, create: bool = True) -> "NodePort":
        if self.outports:
            if len(self.outports) != 1:
                raise ValueError(f"Cannot choose one outport from {self.outports}")
            return self[self.outports[0]]
        return self["value"]

    def __getitem__(self, key: str) -> "NodePort":
        # syntactic sugar for creating references to output ports from node
        return NodePort(self, key)

    def __len__(self) -> int:
        return len(self.outports or [])

    def __iter__(self) -> Iterator["NodePort"]:
        return (self[p] for p in (self.outports or []))


@dataclass(frozen=True)
class NodePort:
    node_ref: NodeRef
    port: PortID

    def __getitem__(self, field_name: str) -> "Unpack":
        raise NotImplementedError(
            "Import tierkreis.builder to get"
            "automatic unpacking of structs using the [<field>] syntax. "
        )


@dataclass(frozen=True)
class TierkreisEdge:
    source: NodePort
    target: NodePort
    type_: Optional[TierkreisType]

    def to_proto(self) -> pg.Edge:
        edge_type = None if self.type_ is None else self.type_.to_proto()
        return pg.Edge(
            port_from=self.source.port,
            node_from=self.source.node_ref.idx,
            port_to=self.target.port,
            node_to=self.target.node_ref.idx,
            edge_type=cast(pg.Type, edge_type),
        )

    def to_edge_handle(self) -> "_EdgeData":
        return (
            self.source.node_ref.idx,
            self.target.node_ref.idx,
            (self.source.port, self.target.port),
        )


# allow specifying input as a port, node with single output
IncomingWireType = Union[NodePort, NodeRef]


def to_nodeport(n: IncomingWireType) -> NodePort:
    return n if isinstance(n, NodePort) else n.default_nodeport()


_EdgeData = Tuple[int, int, Tuple[str, str]]


def _to_edgedata(edgeit: Iterable[Any]) -> Iterator[_EdgeData]:
    return (
        (src, dest, (cast(str, srcport), cast(str, destport)))
        for (src, dest, (srcport, destport)) in edgeit
    )


class MismatchedGraphs(Exception):
    def __init__(self, graph: "TierkreisGraph", endpoint: NodeRef):
        self.graph = graph
        self.endpoint = endpoint
        super().__init__("Cannot add an edge whose endpoint is on a different graph")


class TierkreisGraph:
    """TierkreisGraph."""

    input_node_idx: int = 0
    output_node_idx: int = 1

    @dataclass(frozen=True)
    class MissingEdge(Exception):
        source: NodePort
        target: NodePort

    def __init__(self, name: str = "") -> None:
        self.name = name
        self._graph = nx.MultiDiGraph()
        inp = self.add_node(InputNode())
        assert inp.idx == self.input_node_idx
        output = self.add_node(OutputNode())
        assert output.idx == self.output_node_idx

        self.input_order: list[str] = []
        self.output_order: list[str] = []

    @property
    def input(self) -> NodeRef:
        return NodeRef(self.input_node_idx, self)

    @property
    def output(self) -> NodeRef:
        return NodeRef(self.output_node_idx, self)

    def inputs(self) -> List[str]:
        return [edge.source.port for edge in self.out_edges(self.input)]

    def outputs(self) -> List[str]:
        return [edge.target.port for edge in self.in_edges(self.output)]

    @property
    def n_nodes(self) -> int:
        return len(self._graph)

    def add_node(
        self,
        _tk_node: TierkreisNode,
        /,
        **incoming_wires: IncomingWireType,
    ) -> NodeRef:
        node_ref = NodeRef(self._graph.number_of_nodes(), self)
        self._graph.add_node(node_ref.idx, node_info=_tk_node)
        for target_port_name, source in incoming_wires.items():
            self.add_edge(source, node_ref[target_port_name])

        return node_ref

    def add_func(
        self,
        _tk_function: Union[str, FunctionName],
        _retry_secs: Optional[int] = None,
        /,
        **kwargs: IncomingWireType,
    ) -> NodeRef:
        f_name: FunctionName = (
            FunctionName.parse(_tk_function)
            if isinstance(_tk_function, str)
            else _tk_function
        )

        return self.add_node(FunctionNode(f_name, _retry_secs), **kwargs)

    def add_const(self, value: Any) -> NodeRef:
        return self.add_node(ConstNode(TierkreisValue.from_python(value)))

    def add_box(
        self,
        graph: "TierkreisGraph",
        /,
        **kwargs: IncomingWireType,
    ) -> NodeRef:
        # TODO restrict to graph i/o
        return self.add_node(BoxNode(graph, Location([])), **kwargs)

    def add_match(
        self,
        variant_value: IncomingWireType,
        /,
        **variant_handlers: IncomingWireType,
    ) -> NodeRef:
        return self.add_node(
            MatchNode(), variant_value=variant_value, **variant_handlers
        )

    def add_tag(
        self,
        tag: str,
        *,  # Following are keyword only
        value: IncomingWireType,
    ) -> NodeRef:
        return self.add_node(TagNode(tag), value=value)

    def insert_graph(
        self,
        graph: "TierkreisGraph",
        /,
        **kwargs: IncomingWireType,
    ) -> Dict[str, IncomingWireType]:
        """Given a graph and wires to connect to that graph's inputs,
        inline that graph into <self>, and return the outputs of
        the inserted graph."""

        index_map: Dict[int, int] = dict()
        for node_idx, node in enumerate(graph.nodes()):
            if node_idx not in {graph.input_node_idx, graph.output_node_idx}:
                index_map[node_idx] = self.add_node(node).idx

        return_outputs: Dict[str, IncomingWireType] = {}

        for edge in graph.edges():
            source_node = edge.source.node_ref.idx
            target_node = edge.target.node_ref.idx
            source_port = (
                kwargs[edge.source.port]
                if source_node == graph.input_node_idx
                else NodeRef(index_map[source_node], self)[edge.source.port]
            )

            if target_node == graph.output_node_idx:
                return_outputs[edge.target.port] = source_port
            else:
                target_port = NodeRef(index_map[target_node], self)[edge.target.port]

                self.add_edge(source_port, target_port, edge.type_)

        return return_outputs

    def inline_boxes(self, recursive=False) -> "TierkreisGraph":
        """Inline boxes by inserting the graphs they contain in to the parent
        graph. Optionally do this recursively.

        :return: Inlined graph
        :rtype: TierkreisGraph
        """

        graph = copy.deepcopy(self)
        deleted_nodes: list[int] = []
        # Iterate through self.nodes rather than graph.nodes so we can mutate latter
        for node_idx, node in enumerate(self.nodes()):
            if not isinstance(node, BoxNode):
                continue

            boxed_g = node.graph
            if recursive:
                boxed_g = boxed_g.inline_boxes(recursive)

            curr_inputs = graph.in_edges(node_idx)

            incoming_ports = {edge.target.port: edge.source for edge in curr_inputs}
            curr_outputs = [
                graph._to_tkedge(e)
                for e in _to_edgedata(graph._graph.out_edges(node_idx, keys=True))
            ]
            # Removal all incident edges
            graph._graph.remove_edges_from(
                list(graph._graph.out_edges(node_idx))
                + list(graph._graph.in_edges(node_idx))
            )

            deleted_nodes.append(node_idx)

            inserted_outputs = graph.insert_graph(boxed_g, **incoming_ports)

            for edge in curr_outputs:
                graph.add_edge(
                    inserted_outputs[edge.source.port], edge.target, edge.type_
                )
        if deleted_nodes:
            graph.remove_nodes(deleted_nodes)

        return graph

    def nodes(self) -> Iterator[TierkreisNode]:
        return (
            self._graph.nodes[idx]["node_info"]
            for idx in range(self._graph.number_of_nodes())
        )

    def edges(self) -> Iterator[TierkreisEdge]:
        return map(self._to_tkedge, _to_edgedata(self._graph.edges(keys=True)))

    def __getitem__(self, key: Union[int, NodeRef]) -> TierkreisNode:
        name = key.idx if isinstance(key, NodeRef) else key
        return self._graph.nodes[name]["node_info"]

    def __setitem__(self, key: Union[int, NodeRef], node: TierkreisNode):
        name = key.idx if isinstance(key, NodeRef) else key
        self._graph.nodes[name]["node_info"] = node

    def add_edge(
        self,
        source: IncomingWireType,
        node_port_to: NodePort,
        edge_type: Optional[Union[Type, TierkreisType]] = None,
    ) -> TierkreisEdge:
        tk_type = _to_tierkreis_type(edge_type)
        node_port_from = to_nodeport(source)
        if node_port_from.node_ref.graph is not self:
            raise MismatchedGraphs(self, node_port_from.node_ref)
        if node_port_to.node_ref.graph is not self:
            raise MismatchedGraphs(self, node_port_to.node_ref)

        # if port is currently connected to discard, replace that edge
        existing_edge = self.out_edge_from_port(node_port_from)
        if isinstance(existing_edge, TierkreisType):
            tk_type = existing_edge
        elif existing_edge is not None:
            raise ValueError(
                f"Already an edge from {node_port_from} to {existing_edge.target}"
            )
        edge_data = (
            node_port_from.node_ref.idx,
            node_port_to.node_ref.idx,
            (node_port_from.port, node_port_to.port),
        )
        self._graph.add_edge(
            *edge_data,
            type=tk_type,
        )

        return self._to_tkedge(edge_data)

    def remove_edge(self, edge: TierkreisEdge):
        assert edge.source.node_ref.graph is self
        assert edge.target.node_ref.graph is self
        self._graph.remove_edge(
            edge.source.node_ref.idx,
            edge.target.node_ref.idx,
            (edge.source.port, edge.target.port),
        )

    def remove_nodes(self, nodes: Iterable[int]):
        self._graph.remove_nodes_from(nodes)
        # shift node indices to account for missing nodes
        # without this step indices will not be contiguous
        nx.relabel_nodes(
            self._graph,
            {n: i for i, n in enumerate(sorted(self._graph.nodes()))},
            copy=False,
        )

    def annotate_input(
        self, input_port: str, edge_type: Optional[Union[Type, TierkreisType]]
    ):
        (in_edge,) = [
            e
            for e in _to_edgedata(self._graph.out_edges(self.input_node_idx, keys=True))
            if e[2][0] == input_port
        ]
        tk_type = _to_tierkreis_type(edge_type)
        self._graph.edges[in_edge]["type"] = tk_type

    def annotate_output(
        self, output_port: str, edge_type: Optional[Union[Type, TierkreisType]]
    ):
        (out_edge,) = [
            e
            for e in _to_edgedata(self._graph.in_edges(self.output_node_idx, keys=True))
            if e[2][1] == output_port
        ]

        tk_type = _to_tierkreis_type(edge_type)
        self._graph.edges[out_edge]["type"] = tk_type

    def get_edge(self, source: NodePort, target: NodePort) -> TierkreisEdge:
        try:
            return next(
                e for e in self.out_edges(source.node_ref) if e.target == target
            )
        except StopIteration as e:
            raise self.MissingEdge(source, target) from e

    def set_outputs(self, **kwargs: IncomingWireType) -> None:
        for out_name, port in kwargs.items():
            self.add_edge(port, self.output[out_name])

    def _to_tkedge(self, handle: _EdgeData) -> TierkreisEdge:
        src, tgt, (src_port, tgt_port) = handle
        edge_data = cast(
            Mapping, self._graph.get_edge_data(src, tgt, (src_port, tgt_port))
        )
        return TierkreisEdge(
            NodeRef(src, self)[src_port],
            NodeRef(tgt, self)[tgt_port],
            edge_data["type"],
        )

    def in_edges(self, node: Union[NodeRef, int]) -> Iterator[TierkreisEdge]:
        node_name = node if isinstance(node, int) else node.idx
        return map(
            self._to_tkedge, _to_edgedata(self._graph.in_edges(node_name, keys=True))
        )

    def out_edges(self, node: Union[NodeRef, int]) -> Iterator[TierkreisEdge]:
        node_idx = node if isinstance(node, int) else node.idx
        return map(
            self._to_tkedge,
            _to_edgedata(self._graph.out_edges(node_idx, keys=True)),
        )

    def discard(self, out_port: NodePort) -> None:
        _ = self.add_func("discard", value=out_port)

    def make_pair(
        self, first_port: IncomingWireType, second_port: IncomingWireType
    ) -> NodePort:
        make_n = self.add_func("make_pair", first=first_port, second=second_port)
        return make_n["pair"]

    def unpack_pair(self, pair_port: IncomingWireType) -> Tuple[NodePort, NodePort]:
        unp_n = self.add_func("unpack_pair", pair=pair_port)
        return unp_n["first"], unp_n["second"]

    def make_vec(self, element_ports: List[IncomingWireType]) -> NodePort:
        vec_port = self.add_const(list())["value"]

        for port in element_ports:
            vec_port = self.add_func("push", vec=vec_port, item=port)["vec"]

        return vec_port

    def vec_last_n_elems(self, vec_port: NodePort, n_elements: int) -> List[NodePort]:
        curr_arr = vec_port
        outports: List[NodePort] = []
        for _ in range(n_elements):
            pop = self.add_func("pop", vec=curr_arr)
            curr_arr = pop["vec"]
            outports.insert(0, pop["item"])
        return outports

    def copy_value(self, value: IncomingWireType) -> Tuple[NodePort, NodePort]:
        copy_n = self.add_func("copy", value=value)

        return copy_n["value_0"], copy_n["value_1"]

    def out_edge_from_port(self, source: NodePort) -> Optional[TierkreisEdge]:
        """
        If there is an edge at port, return it, else None.
        """
        out_edges = [
            out_edge
            for out_edge in self.out_edges(source.node_ref)
            if out_edge.source.port == source.port
        ]
        if len(out_edges) == 0:
            return None
        (out_edge,) = out_edges
        return out_edge

    def to_proto(self) -> pg.Graph:
        pg_graph = pg.Graph()
        pg_graph.nodes = [n.to_proto() for n in self.nodes()]
        pg_graph.edges = [e.to_proto() for e in self.edges()]
        pg_graph.name = self.name
        pg_graph.input_order = self.input_order
        pg_graph.output_order = self.output_order
        return pg_graph

    @classmethod
    def from_proto(cls, pg_graph: pg.Graph) -> "TierkreisGraph":
        tk_graph = cls()
        tk_graph.name = pg_graph.name
        tk_graph.input_order = pg_graph.input_order
        tk_graph.output_order = pg_graph.output_order

        for pgn in pg_graph.nodes[2:]:
            tk_graph.add_node(TierkreisNode.from_proto(pgn))

        for pg_edge in pg_graph.edges:
            source_node = NodeRef(pg_edge.node_from, tk_graph)
            target_node = NodeRef(pg_edge.node_to, tk_graph)
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

    def __call__(
        self: "TierkreisGraph", *args: "ValueSource", **kwargs: "ValueSource"
    ) -> NodeRef:
        raise NotImplementedError(
            "TierkreisGraph can only be called inside builder contexts."
        )


def _to_tierkreis_type(
    edge_type: Optional[Union[Type, TierkreisType]],
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

    @property
    def _instance_pytype(self) -> typing.Type:
        return TierkreisGraph

    def to_proto(self) -> pg.Value:
        return pg.Value(graph=self.value.to_proto())

    def _to_python_impl(self, type_: typing.Type[T]) -> T | None:
        from tierkreis.core.python import RuntimeGraph

        if isinstance(type_, typing.TypeVar):
            return cast(T, self)
        if typing.get_origin(type_) is RuntimeGraph:
            return cast(T, RuntimeGraph(self.value))
        if issubclass(type_, TierkreisGraph):
            return cast(T, self.value)

    @classmethod
    def from_proto(cls, value: Any) -> "TierkreisValue":
        return cls(TierkreisGraph.from_proto(cast(pg.Graph, value)))

    def __str__(self) -> str:
        return "GraphValue"

    def viz_str(self) -> str:
        return "Graph"


# allow graph displays in jupyter notebooks
from tierkreis.core.graphviz import tierkreis_to_graphviz  # noqa: E402

setattr(
    TierkreisGraph,
    "_repr_svg_",
    lambda self: tierkreis_to_graphviz(self)._repr_svg_(),  # type: ignore
)
