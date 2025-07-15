import json
from typing import Optional, assert_never

from pydantic import BaseModel
from tierkreis.controller.data.core import NodeIndex
from tierkreis.controller.data.location import WorkerCallArgs, Loc
from tierkreis.controller.data.graph import GraphData, IfElse
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


def add_conditional_edges(
    storage: ControllerStorage,
    loc: Loc,
    i: NodeIndex,
    node: IfElse,
    py_edges: list[PyEdge],
):
    try:
        pred = json.loads(storage.read_output(loc.N(node.pred[0]), node.pred[1]))
    except FileNotFoundError:
        pred = None

    refs = {True: node.if_true, False: node.if_false}

    for branch, (idx, p) in refs.items():
        if p in storage.read_output_ports(loc.N(idx)):
            value = json.loads(storage.read_output(loc.N(idx), p))
        else:
            value = None
        edge = PyEdge(
            from_node=idx,
            from_port=p,
            to_node=i,
            to_port=f"If{branch}",
            conditional=pred is None or pred != branch,
            value=value,
        )
        py_edges.append(edge)


def get_eval_node(
    storage: ControllerStorage, node_location: Loc, errored_nodes: list[Loc]
) -> EvalNodeData:
    thunk = storage.read_output(node_location.N(-1), "body")
    graph = GraphData(**json.loads(thunk))

    pynodes: list[PyNode] = []
    py_edges: list[PyEdge] = []

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
            case "ifelse":
                name = node.type
                add_conditional_edges(storage, node_location, i, node, py_edges)
            case "const" | "map" | "eval" | "input" | "output" | "loop" | "eifelse":
                name = node.type
            case _:
                assert_never(node)

        pynode = PyNode(
            id=i, status=status, function_name=name, node_location=new_location
        )
        pynodes.append(pynode)

        for p0, (idx, p1) in in_edges(node).items():
            value = None
            if p1 in storage.read_output_ports(node_location.N(idx)):
                value = json.loads(storage.read_output(node_location.N(idx), p1))

            py_edge = PyEdge(
                from_node=idx, from_port=p1, to_node=i, to_port=p0, value=value
            )
            py_edges.append(py_edge)

    return EvalNodeData(nodes=pynodes, edges=py_edges)
