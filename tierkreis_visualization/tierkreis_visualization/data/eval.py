import json
from typing import Optional, assert_never

from pydantic import BaseModel
from tierkreis.controller.data.location import WorkerCallArgs, Loc
from tierkreis.controller.data.graph import GraphData
from tierkreis.controller.storage.adjacency import in_edges
from tierkreis.controller.storage.protocol import ControllerStorage

from tierkreis_visualization.data.models import PyNode, NodeStatus, PyEdge


class EvalNodeData(BaseModel):
    nodes: list[PyNode]
    edges: list[PyEdge]


def node_status(
    is_finished: bool, definition: Optional[WorkerCallArgs], has_error: bool = False
) -> NodeStatus:
    if is_finished:
        return "Finished"

    if definition is not None:
        if has_error:
            return "Error"
        return "Started"

    return "Not started"


def check_error(node_location: Loc, errored_nodes: list[Loc]) -> bool:
    return any(node.startswith(node_location) for node in errored_nodes)


def get_eval_node(
    storage: ControllerStorage, node_location: Loc, errored_nodes: list[Loc]
) -> EvalNodeData:
    thunk = storage.read_output(node_location.N(-1), "body")
    graph = GraphData(**json.loads(thunk))

    pynodes: list[PyNode] = []
    for i, node in enumerate(graph.nodes):
        new_location = node_location.N(i)
        is_finished = storage.is_node_finished(new_location)
        has_error = check_error(new_location, errored_nodes)
        try:
            definition = storage.read_worker_call_args(new_location)
        except FileNotFoundError:
            definition = None

        status = node_status(is_finished, definition, has_error)

        match node.type:
            case "function":
                name = node.function_name
            case "const" | "map" | "eval" | "input" | "output" | "loop" | "ifelse":
                name = node.type
            case _:
                assert_never(node)

        pynode = PyNode(id=i, status=status, function_name=name)
        pynodes.append(pynode)

    py_edges: list[PyEdge] = []
    for idx, node in enumerate(graph.nodes):
        for p0, (i, p1) in in_edges(node).items():
            py_edge = PyEdge(from_node=i, from_port=p1, to_node=idx, to_port=p0)
            py_edges.append(py_edge)

    return EvalNodeData(nodes=pynodes, edges=py_edges)
