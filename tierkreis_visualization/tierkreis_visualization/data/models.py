from typing import Literal, Any
from pydantic import BaseModel

NodeStatus = Literal["Not started", "Started", "Error", "Finished"]


class PyNode(BaseModel):
    id: int
    status: NodeStatus
    function_name: str
    node_location: str = ""
    value: Any | None = None
    started_time: str
    finished_time: str


class PyEdge(BaseModel):
    from_node: int
    from_port: str
    to_node: int
    to_port: str
    value: Any | None = None
    conditional: bool = False
