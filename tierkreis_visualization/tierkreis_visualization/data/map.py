from pydantic import BaseModel
from tierkreis.controller.data.location import Loc
from tierkreis.controller.storage.protocol import ControllerStorage
from tierkreis.controller.data.graph import Map
from tierkreis.exceptions import TierkreisError

from tierkreis_visualization.data.eval import check_error
from tierkreis_visualization.data.models import PyEdge, PyNode


class MapNodeData(BaseModel):
    nodes: list[PyNode]
    edges: list[PyEdge]


def get_map_node(
    storage: ControllerStorage, loc: Loc, map: Map, errored_nodes: list[Loc]
) -> MapNodeData:
    parent = loc.parent()
    if parent is None:
        raise TierkreisError("MAP node must have parent.")

    map_eles = storage.read_output_ports(parent.N(map.input_idx))
    nodes: list[PyNode] = []
    for ele in map_eles:
        node = PyNode(id=ele, status="Started", function_name=ele)
        if check_error(loc.M(ele), errored_nodes):
            node.status = "Error"
        elif storage.is_node_finished(loc.M(ele)):
            node.status = "Finished"
        nodes.append(node)

    return MapNodeData(nodes=nodes, edges=[])
