from pydantic import BaseModel
from tierkreis.controller.data.location import Loc
from tierkreis.controller.storage.protocol import ControllerStorage
from tierkreis import Labels

from tierkreis_visualization.data.eval import check_error
from tierkreis_visualization.data.models import PyNode, PyEdge


class LoopNodeData(BaseModel):
    nodes: list[PyNode]
    edges: list[PyEdge]


def get_loop_node(
    storage: ControllerStorage, node_location: Loc, errored_nodes: list[Loc]
) -> LoopNodeData:
    i = 0
    while storage.is_node_started(node_location.L(i + 1)):
        i += 1
    new_location = node_location.L(i)

    nodes = [PyNode(id=n, status="Finished", function_name=f"L{n}") for n in range(i)]

    if check_error(node_location, errored_nodes):
        last_status = "Error"
    elif storage.is_node_finished(new_location):
        last_status = "Finished"
    else:
        last_status = "Started"
    nodes.append(PyNode(id=i, status=last_status, function_name=f"L{i}"))

    edges = [
        PyEdge(from_node=n, from_port=Labels.VALUE, to_node=n + 1, to_port=Labels.VALUE)
        for n in range(i)
    ]

    return LoopNodeData(nodes=nodes, edges=edges)
