from pydantic import BaseModel
from tierkreis.controller.data.location import Loc, WorkerCallArgs
from tierkreis_visualization.data.models import PyNode, PyEdge
from tierkreis_visualization.data.function import (
    FunctionDefinition,
)


class PyGraph(BaseModel):
    nodes: list[PyNode]
    edges: list[PyEdge]


class BaseNodeData(BaseModel):
    name: str
    url: str
    node_location: str
    breadcrumbs: list[tuple[str, str]]


class NodeDataPyGraph(PyGraph, BaseNodeData):
    pass


class PyDefinition(BaseModel):
    definition: WorkerCallArgs
    # Can be None as a fallback.
    function: FunctionDefinition | None


class NodeDataDefinition(PyDefinition, BaseNodeData):
    pass


NodeData = NodeDataPyGraph | NodeDataDefinition
