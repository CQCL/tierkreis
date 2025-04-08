from enum import StrEnum

from pydantic import BaseModel, field_serializer


class NodeStatus(StrEnum):
    NOT_STARTED = "Not started"
    STARTED = "Started"
    FINISHED = "Finished"


class PyNode(BaseModel):
    id: int
    status: NodeStatus
    function_name: str


class PyEdge(BaseModel):
    from_node: int
    from_port: str
    to_node: int
    to_port: str
