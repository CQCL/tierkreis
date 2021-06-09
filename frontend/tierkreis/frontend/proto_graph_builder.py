from typing import Dict, Optional, Tuple, IO, Type, Union


import tierkreis.core.protos.tierkreis.graph as pg
from tierkreis.core import (
    encode_value,
    from_python_type,
    GraphIOType,
    Value
)


class ProtoGraphBuilder:
    def __init__(self) -> None:
        self._g = pg.Graph()
        self._input_types: Dict[str, Type] = dict()
        self._output_types: Dict[str, Type] = dict()
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

    def add_const(
        self,
        name: str,
        value: Value
    ) -> str:
        self._g.nodes[name] = pg.Node(const=encode_value(value))
        return name

    def add_box(
        self,
        name: str,
        graph: Union["ProtoGraphBuilder", pg.Graph]
    ) -> str:
        if isinstance(graph, ProtoGraphBuilder):
            self._g.nodes[name] = pg.Node(box=graph._g)
        else:
            self._g.nodes[name] = pg.Node(box=graph)
        return name

    def add_edge(
        self,
        node_port_from: Tuple[str, str],
        node_port_to: Tuple[str, str],
        edge_type: Type,
    ):
        new_edge = pg.Edge()
        new_edge.node_from, new_edge.port_from = node_port_from
        new_edge.node_to, new_edge.port_to = node_port_to
        new_edge.edge_type = from_python_type(edge_type) 
        self._g.edges.append(new_edge)

        if node_port_from[0] == "input":
            self._input_types[node_port_from[1]] = edge_type
        if node_port_to[0] == "output":
            self._output_types[node_port_to[1]] = edge_type

    def register_input(self, name: str, edge_type: Type, node_port: Tuple[str, str]):
        self._input_types[name] = edge_type
        self.add_edge((self.input_node, name), node_port, edge_type)

    def register_output(self, name: str, edge_type: Type, node_port: Tuple[str, str]):
        self._output_types[name] = edge_type
        self.add_edge(node_port, (self.output_node, name), edge_type)

    def get_type(self) -> GraphIOType:
        return GraphIOType(
            "ProtoGraphBuilder",
            (ProtoGraphBuilder,),
            {"inputs": self._input_types, "outputs": self._output_types},
        )

    def write_to_file(self, fp: IO[bytes]):
        fp.write(self._g.SerializeToString())

    @classmethod
    def read_from_file(cls, fp: IO[bytes]) -> "ProtoGraphBuilder":
        new = cls()
        new._g.parse(fp.read())
        return new
