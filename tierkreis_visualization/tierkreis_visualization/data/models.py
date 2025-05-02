from typing import Literal
from pydantic import BaseModel


NodeStatus = Literal["Not started", "Started", "Finished"]


class PyNode(BaseModel):
    id: int
    status: NodeStatus
    function_name: str


class PyEdge(BaseModel):
    from_node: int
    from_port: str
    to_node: int
    to_port: str
