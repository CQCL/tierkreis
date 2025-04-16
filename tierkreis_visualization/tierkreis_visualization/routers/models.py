from typing import assert_never

from pydantic import BaseModel, Field

from tierkreis_visualization.data.models import PyNode, NodeStatus, PyEdge


def color_from_status(status: NodeStatus) -> str:
    match status:
        case NodeStatus.NOT_STARTED:
            return "#D3D3D3"
        case NodeStatus.STARTED:
            return "#00FF00"
        case NodeStatus.FINISHED:
            return "#42f5ec"
        case _:
            assert_never(status)


class JSNode(BaseModel):
    id: int
    title: str
    label: str
    shape: str
    color: str

    @staticmethod
    def from_pynode(pynode: PyNode):
        title = f"Function name: {pynode.function_name}\nStatus: {pynode.status}"

        return JSNode(
            id=pynode.id,
            title=title,
            label=pynode.function_name,
            color=color_from_status(pynode.status),
            shape="box",
        )


class JSEdge(BaseModel):
    id: str
    from_node: int = Field(..., serialization_alias="from")
    to: int
    title: str
    label: str
    arrows: str = "to"

    @staticmethod
    def from_py_edge(py_edge: PyEdge):
        return JSEdge(
            id=f"{py_edge.from_port}->{py_edge.to_port}:{py_edge.from_node}->{py_edge.to_node}",
            from_node=py_edge.from_node,
            to=py_edge.to_node,
            title=f"{py_edge.from_port}->{py_edge.to_port}",
            label=py_edge.to_port,
        )


class JSGraph(BaseModel):
    nodes: list[JSNode]
    edges: list[JSEdge]

    @staticmethod
    def from_python(nodes: list[PyNode], edges: list[PyEdge]):
        js_nodes = [JSNode.from_pynode(x) for x in nodes]
        js_edges = [JSEdge.from_py_edge(x) for x in edges]
        return JSGraph(nodes=js_nodes, edges=js_edges)
