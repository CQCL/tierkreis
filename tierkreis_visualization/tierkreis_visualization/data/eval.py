from typing import Optional

from pydantic import BaseModel
from tierkreis import TierkreisGraph
from tierkreis.controller.models import NodeDefinition, NodeLocation
from tierkreis.controller.storage.protocol import ControllerStorage
from tierkreis.core import Labels
from tierkreis.core.protos.tierkreis.v1alpha1.graph import Graph

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
    thunk = storage.read_output(node_location.append_node(0), Labels.THUNK)
    graph_value = Graph.FromString(thunk)
    graph = TierkreisGraph.from_proto(graph_value)

    pynodes: list[PyNode] = []
    for i in range(graph.n_nodes):
        new_location = node_location.append_node(i)
        is_finished = storage.is_node_finished(new_location)
        try:
            definition = storage.read_node_definition(new_location)
        except FileNotFoundError:
            definition = None

        status = node_status(is_finished, definition)
        name = definition.function_name if definition else graph[i].__class__.__name__

        pynode = PyNode(id=i, status=status, function_name=name)
        pynodes.append(pynode)

    py_edges: list[PyEdge] = []
    for edge in graph.edges():
        py_edge = PyEdge(
            from_node=edge.source.node_ref.idx,
            from_port=edge.source.port,
            to_node=edge.target.node_ref.idx,
            to_port=edge.target.port,
        )
        py_edges.append(py_edge)

    return EvalNodeData(nodes=pynodes, edges=py_edges)
