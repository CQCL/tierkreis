"""Utilities for building tierkreis graphs."""
from typing import IO, Dict, List, Optional, Set, Tuple, Type, Union, Any

import tierkreis.core.protos.tierkreis.graph as pg
from tierkreis.core.values import TierkreisValue
from tierkreis.core.types import TierkreisType

# from tierkreis.core import Value, encode_value, from_python_type


class ProtoGraphBuilder:
    """Builder for tierkreis graphs."""

    def __init__(self) -> None:
        self._g = pg.Graph()
        self._input_types: Dict[str, Optional[TierkreisType]] = dict()
        self._output_types: Dict[str, Optional[TierkreisType]] = dict()
        self._g.nodes["input"] = pg.Node(input=pg.Empty())
        self._g.nodes["output"] = pg.Node(output=pg.Empty())

    @property
    def graph(self) -> pg.Graph:
        return self._g

    @property
    def n_nodes(self) -> int:
        return len(self._g.nodes)

    @property
    def input_node(self) -> str:
        return "input"

    @property
    def output_node(self) -> str:
        return "output"

    def add_node(
        self,
        name: str,
        function: str,
    ) -> str:
        self._g.nodes[name] = pg.Node(function=function)
        return name

    def add_const(self, name: str, value: Any) -> str:
        self._g.nodes[name] = pg.Node(
            const=TierkreisValue.from_python(value).to_proto()
        )
        return name

    def add_box(self, name: str, graph: Union["ProtoGraphBuilder", pg.Graph]) -> str:
        if isinstance(graph, ProtoGraphBuilder):
            self._g.nodes[name] = pg.Node(box=graph.graph)
        else:
            self._g.nodes[name] = pg.Node(box=graph)
        return name

    @property
    def node_names(self) -> Set[str]:
        return set(self._g.nodes.keys())

    def add_edge(
        self,
        node_port_from: Tuple[str, str],
        node_port_to: Tuple[str, str],
        edge_type: Optional[Union[Type, TierkreisType]] = None,
    ):
        new_edge = pg.Edge()
        new_edge.node_from, new_edge.port_from = node_port_from
        new_edge.node_to, new_edge.port_to = node_port_to
        self._g.edges.append(new_edge)

        if edge_type is None:
            tierkreis_type = None
        elif isinstance(edge_type, TierkreisType):
            tierkreis_type = edge_type
            new_edge.edge_type = tierkreis_type.to_proto()
        else:
            tierkreis_type = TierkreisType.from_python(edge_type)
            new_edge.edge_type = tierkreis_type.to_proto()

        if node_port_from[0] == "input":
            self._input_types[node_port_from[1]] = tierkreis_type
        if node_port_to[0] == "output":
            self._output_types[node_port_to[1]] = tierkreis_type

    def register_input(self, name: str, edge_type: Type, node_port: Tuple[str, str]):
        self._input_types[name] = edge_type
        self.add_edge((self.input_node, name), node_port, edge_type)

    def register_output(self, name: str, edge_type: Type, node_port: Tuple[str, str]):
        self._output_types[name] = edge_type
        self.add_edge(node_port, (self.output_node, name), edge_type)

    def incoming_edges(self, node: str) -> List[pg.Edge]:
        return [e for e in self._g.edges if e.node_to == node]

    def outgoing_edges(self, node: str) -> List[pg.Edge]:
        return [e for e in self._g.edges if e.node_from == node]

    def input_edges(self) -> List[pg.Edge]:
        return self.outgoing_edges(self.input_node)

    def output_edges(self) -> List[pg.Edge]:
        return self.incoming_edges(self.output_node)

    def remove_edge(
        self, node_port_from: Tuple[str, str], node_port_to: Tuple[str, str]
    ) -> pg.Edge:

        edge = next(
            (
                e
                for e in self._g.edges
                if ((e.node_from, e.port_from), (e.node_to, e.port_to))
                == (node_port_from, node_port_to)
            )
        )
        self._g.edges.remove(edge)
        return edge

    def get_type(self) -> Type:
        return type(
            "ProtoGraphBuilder",
            (ProtoGraphBuilder,),
            {"inputs": self._input_types, "outputs": self._output_types},
        )

    def write_to_file(self, file_pointer: IO[bytes]):
        file_pointer.write(self._g.SerializeToString())

    @classmethod
    def read_from_file(cls, file_pointer: IO[bytes]) -> "ProtoGraphBuilder":
        new = cls()
        new._g.parse(file_pointer.read())
        return new
