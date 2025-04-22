from math import ceil, sqrt
from pydantic import BaseModel
from tierkreis.controller.data.location import Loc
from tierkreis.controller.storage.protocol import ControllerStorage

from tierkreis_visualization.data.models import PyEdge, PyNode, NodeStatus


class MapNodeData(BaseModel):
    nodes: list[PyNode]
    edges: list[PyEdge]


def get_map_node(storage: ControllerStorage, node_location: Loc) -> MapNodeData:
    i = 0
    nodes: list[PyNode] = []
    while True:
        loc = node_location.M(i)
        if not storage.is_node_started(loc):
            break

        node = PyNode(id=i, status=NodeStatus.STARTED, function_name=f"M{i}")
        nodes.append(node)
        i += 1

        if storage.is_node_finished(loc):
            node.status = NodeStatus.FINISHED
            continue

    edges: list[PyEdge] = []
    N = ceil(sqrt(i))
    for col in range(N):
        for row in range(N - 1):
            edges.append(
                PyEdge(
                    from_node=row + N * col,
                    to_node=row + N * col + 1,
                    from_port=str(row),
                    to_port=str(col),
                )
            )

    return MapNodeData(nodes=nodes, edges=edges)
