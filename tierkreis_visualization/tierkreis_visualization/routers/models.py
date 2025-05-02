from pydantic import BaseModel
from tierkreis_visualization.data.models import PyNode, PyEdge


class PyGraph(BaseModel):
    nodes: list[PyNode]
    edges: list[PyEdge]
