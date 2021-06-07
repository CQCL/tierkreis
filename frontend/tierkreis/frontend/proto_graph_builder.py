from typing import Dict, Optional, Tuple, IO, Type


import tierkreis.core.protos.tierkreis.graph as pg
from tierkreis.core import (
    encode_values,
    PyValMap,
    from_python_type,
    GraphIOType,
)


class ProtoGraphBuilder:
    def __init__(self) -> None:
        self._g = pg.Graph()
        self._input_types: Dict[str, Type] = dict()
        self._output_types: Dict[str, Type] = dict()
        self._input_node: Optional[int] = None
        self._output_node: Optional[int] = None

    @property
    def graph(self) -> pg.Graph:
        return self._g

    @property
    def n_nodes(self) -> int:
        return len(self._g.nodes)

    @property
    def input_node(self) -> int:
        if self._input_node is None:
            self._input_node = self.add_node("input", "builtin/input")

        return self._input_node

    @property
    def output_node(self) -> int:
        if self._output_node is None:
            self._output_node = self.add_node("output", "builtin/output")

        return self._output_node

    def add_node(
        self,
        name: str,
        op: str,
        pre_args: Optional[PyValMap] = None,
    ) -> int:
        new_node = pg.NodeWeight()
        new_node.id = self.n_nodes
        new_node.name = name
        new_node.op = op
        if pre_args:
            new_node.pre_args.map = encode_values(pre_args)

        self._g.nodes.append(new_node)
        return new_node.id

    def add_edge(
        self,
        node_port_from: Tuple[int, str],
        node_port_to: Tuple[int, str],
        edge_type: Type,
    ):
        new_edge = pg.EdgeWeight()
        new_edge.node_from, new_edge.port_from = node_port_from
        new_edge.node_to, new_edge.port_to = node_port_to
        new_edge.edge_type = from_python_type(edge_type)
        self._g.edges.append(new_edge)

    def register_input(self, name: str, edge_type: Type, node_port: Tuple[int, str]):
        self._input_types[name] = edge_type
        self.add_edge((self.input_node, name), node_port, edge_type)

    def register_output(self, name: str, edge_type: Type, node_port: Tuple[int, str]):
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
