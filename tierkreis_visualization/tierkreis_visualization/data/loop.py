from pydantic import BaseModel
from tierkreis.controller.data.location import Loc
from tierkreis.controller.storage.protocol import ControllerStorage
from tierkreis.core import Labels

from tierkreis_visualization.data.models import PyNode, PyEdge, NodeStatus


class LoopNodeData(BaseModel):
    nodes: list[PyNode]
    edges: list[PyEdge]


def get_loop_node(storage: ControllerStorage, node_location: Loc) -> LoopNodeData:
    i = 0
    while storage.is_node_started(node_location.L(i + 1)):
        i += 1
    new_location = node_location.N(i)

    nodes = [
        PyNode(id=n, status=NodeStatus.FINISHED, function_name=f"L{n}")
        for n in range(i)
    ]

    last_status = (
        NodeStatus.FINISHED
        if storage.is_node_finished(new_location)
        else NodeStatus.STARTED
    )
    nodes.append(PyNode(id=i, status=last_status, function_name=f"L{i}"))

    edges = [
        PyEdge(from_node=n, from_port=Labels.VALUE, to_node=n + 1, to_port=Labels.VALUE)
        for n in range(i)
    ]

    return LoopNodeData(nodes=nodes, edges=edges)
