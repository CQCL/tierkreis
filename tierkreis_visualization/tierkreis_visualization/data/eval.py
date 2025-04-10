import json
from typing import Optional, assert_never

from pydantic import BaseModel
from tierkreis.controller.data.location import NodeDefinition, NodeLocation
from tierkreis.controller.data.graph import GraphData
from tierkreis.controller.storage.protocol import ControllerStorage
from tierkreis.core import Labels

from tierkreis_visualization.data.models import PyNode, NodeStatus, PyEdge


class EvalNodeData(BaseModel):
    nodes: list[PyNode]
    edges: list[PyEdge]


def node_status(is_finished: bool, definition: Optional[NodeDefinition]) -> NodeStatus:
    if is_finished:
        return NodeStatus.FINISHED

    if definition is not None:
        return NodeStatus.STARTED

    return NodeStatus.NOT_STARTED


def get_eval_node(
    storage: ControllerStorage, node_location: NodeLocation
) -> EvalNodeData:
    thunk = storage.read_output(node_location.append_node(-1), Labels.THUNK)
    graph = GraphData(**json.loads(thunk))

    pynodes: list[PyNode] = []
    for i, node in enumerate(graph.nodes):
        new_location = node_location.append_node(i)
        is_finished = storage.is_node_finished(new_location)
        try:
            definition = storage.read_node_definition(new_location)
        except FileNotFoundError:
            definition = None

        status = node_status(is_finished, definition)

        match node.type:
            case "function":
                name = node.function_name
            case "const" | "map" | "eval" | "input" | "output" | "loop":
                name = node.type
            case _:
                assert_never(node)

        pynode = PyNode(id=i, status=status, function_name=name)
        pynodes.append(pynode)

    py_edges: list[PyEdge] = []
    for idx, node in enumerate(graph.nodes):
        for l, (i, p) in node.inputs.items():
            py_edge = PyEdge(from_node=i, from_port=p, to_node=idx, to_port=l)
            py_edges.append(py_edge)

    return EvalNodeData(nodes=pynodes, edges=py_edges)
