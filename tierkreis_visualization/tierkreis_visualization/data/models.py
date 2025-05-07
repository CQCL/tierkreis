from typing import Literal
from pydantic import BaseModel
from tierkreis.controller.data.graph import PortID

NodeStatus = Literal["Not started", "Started", "Error", "Finished"]


class PyNode(BaseModel):
    id: int | PortID
    status: NodeStatus
    function_name: str


class PyEdge(BaseModel):
    from_node: int
    from_port: str
    to_node: int
    to_port: str
