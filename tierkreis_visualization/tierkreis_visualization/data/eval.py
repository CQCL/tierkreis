import json
from typing import Optional, assert_never

from pydantic import BaseModel
from tierkreis.controller.data.location import WorkerCallArgs, Loc
from tierkreis.controller.data.graph import GraphData, Eval
from tierkreis.controller.storage.protocol import ControllerStorage

from tierkreis_visualization.data.models import PyNode, NodeStatus, PyEdge


class EvalNodeData(BaseModel):
    nodes: list[PyNode]
    edges: list[PyEdge]


def node_status(is_finished: bool, definition: Optional[WorkerCallArgs]) -> NodeStatus:
    if is_finished:
        return NodeStatus.FINISHED

    if definition is not None:
        return NodeStatus.STARTED

    return NodeStatus.NOT_STARTED


def get_eval_node(
    storage: ControllerStorage, node_location: Loc, eval: Eval
) -> EvalNodeData:
    thunk = storage.read_output(eval.body[0], eval.body[1])
    graph = GraphData(**json.loads(thunk))

    pynodes: list[PyNode] = []
    for i, node in graph.nodes.items():
        new_location = node_location + i
        is_finished = storage.is_node_finished(new_location)
        try:
            definition = storage.read_worker_call_args(new_location)
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

        pynode = PyNode(id=i.stem() or -1, status=status, function_name=name)
        pynodes.append(pynode)

    py_edges: list[PyEdge] = []
    for idx, node in graph.nodes.items():
        for p0, (i, p1) in node.inputs.items():
            py_edge = PyEdge(
                from_node=i.stem() or -1,
                from_port=p1,
                to_node=idx.stem() or -1,
                to_port=p0,
            )
            py_edges.append(py_edge)

    return EvalNodeData(nodes=pynodes, edges=py_edges)
