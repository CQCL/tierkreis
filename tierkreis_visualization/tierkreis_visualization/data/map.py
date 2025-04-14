from pydantic import BaseModel
from tierkreis.controller.data.location import NodeLocation
from tierkreis.controller.storage.protocol import ControllerStorage

from tierkreis_visualization.data.models import PyNode, NodeStatus


class MapNodeData(BaseModel):
    nodes: list[PyNode]


def get_map_node(
    storage: ControllerStorage, node_location: NodeLocation
) -> MapNodeData:
    i = 0
    nodes: list[PyNode] = []
    while True:
        loc = node_location.append_map(i)
        i += 1
        if not storage.is_node_started(loc):
            break

        node = PyNode(id=i, status=NodeStatus.STARTED, function_name=f"M{i}")
        nodes.append(node)

        if storage.is_node_finished(loc):
            node.status = NodeStatus.FINISHED
            continue

    return MapNodeData(nodes=nodes)
