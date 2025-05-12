import json
from typing import AsyncIterator
from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel
from starlette.responses import JSONResponse, PlainTextResponse
from tierkreis.controller.data.location import Loc, WorkerCallArgs
from watchfiles import awatch

from tierkreis_visualization.config import (
    CONFIG,
    get_storage,
    templates,
)
from tierkreis_visualization.data.eval import get_eval_node
from tierkreis_visualization.data.function import get_function_node
from tierkreis_visualization.data.loop import get_loop_node
from tierkreis_visualization.data.map import get_map_node
from tierkreis_visualization.data.workflows import get_workflows
from tierkreis_visualization.routers.models import (
    NodeData,
    NodeDataDefinition,
    NodeDataPyGraph,
    PyGraph,
)
from tierkreis_visualization.routers.navigation import breadcrumbs

router = APIRouter(prefix="/workflows")


@router.get("/")
def list_workflows(request: Request) -> HTMLResponse:
    workflows = get_workflows()
    return templates.TemplateResponse(
        request=request, name="workflows.html", context={"workflows": workflows}
    )


class NodeResponse(BaseModel):
    definition: WorkerCallArgs


def parse_node_location(node_location_str: str) -> Loc:
    return Loc(node_location_str)


def get_errored_nodes(workflow_id: UUID) -> list[Loc]:
    storage = get_storage(workflow_id)
    errored_nodes = storage.read_errors(Loc("-"))
    return [parse_node_location(node) for node in errored_nodes.split("\n")]


def get_node_data(workflow_id: UUID, node_location: Loc) -> NodeData:
    storage = get_storage(workflow_id)
    errored_nodes = get_errored_nodes(workflow_id)

    definition = storage.read_worker_call_args(node_location)
    node = storage.read_node_def(node_location)

    pygraph = None
    function = None
    if node.type == "eval":
        data = get_eval_node(storage, node_location, errored_nodes)
        name = "eval.jinja"
        pygraph = PyGraph(nodes=data.nodes, edges=data.edges)
    elif node.type == "loop":
        data = get_loop_node(storage, node_location, errored_nodes)
        name = "loop.jinja"
        pygraph = PyGraph(nodes=data.nodes, edges=data.edges)

    elif node.type == "map":
        data = get_map_node(storage, node_location, node, errored_nodes)
        name = "map.jinja"
        pygraph = PyGraph(nodes=data.nodes, edges=data.edges)

    elif node.type == "function":
        data = get_function_node(storage, node_location)
        name = "function.jinja"

    else:
        name = "fallback.html"

    url = f"/workflows/{workflow_id}/nodes/{node_location}"
    if pygraph is not None:
        return NodeDataPyGraph(
            name=name,
            url=url,
            node_location=node_location,
            breadcrumbs=breadcrumbs(workflow_id, node_location),
            nodes=pygraph.nodes,
            edges=pygraph.edges,
        )
    else:
        return NodeDataDefinition(
            name=name,
            url=url,
            node_location=node_location,
            breadcrumbs=breadcrumbs(workflow_id, node_location),
            definition=definition,
            function=function,
        )


async def node_stream(workflow_id: UUID, node_location: Loc) -> AsyncIterator[str]:
    metadata_path = (
        CONFIG.tierkreis_path / str(workflow_id) / str(node_location) / "_metadata"
    )
    async for _changes in awatch(metadata_path):
        ctx = get_node_data(workflow_id, node_location)
        yield f"event: message\ndata: {json.dumps(ctx)}\n\n"


@router.get("/{workflow_id}/nodes/{node_location_str}", response_model=None)
def get_node(
    request: Request, workflow_id: UUID, node_location_str: str
) -> NodeData | StreamingResponse | HTMLResponse:
    node_location = parse_node_location(node_location_str)
    node_data = get_node_data(workflow_id, node_location)
    if request.headers["Accept"] == "application/json":
        return node_data

    if request.headers["Accept"] == "text/event-stream":
        return StreamingResponse(
            node_stream(workflow_id, node_location), media_type="text/event-stream"
        )

    return templates.TemplateResponse(
        request=request, name=node_data.name, context=node_data.model_dump()
    )


@router.get("/{workflow_id}/nodes/{node_location_str}/inputs/{port_name}")
def get_input(
    workflow_id: UUID, node_location_str: str, port_name: str
) -> JSONResponse:
    node_location = parse_node_location(node_location_str)
    storage = get_storage(workflow_id)
    definition = storage.read_worker_call_args(node_location)

    with open(definition.inputs[port_name], "rb") as fh:
        return JSONResponse(json.loads(fh.read()))


@router.get("/{workflow_id}/nodes/{node_location_str}/outputs/{port_name}")
def get_output(
    workflow_id: UUID, node_location_str: str, port_name: str
) -> JSONResponse:
    node_location = parse_node_location(node_location_str)
    storage = get_storage(workflow_id)
    definition = storage.read_worker_call_args(node_location)

    with open(definition.outputs[port_name], "rb") as fh:
        return JSONResponse(json.loads(fh.read()))


@router.get("/{workflow_id}/nodes/{node_location_str}/logs")
def get_logs(workflow_id: UUID, node_location_str: str) -> PlainTextResponse:
    node_location = parse_node_location(node_location_str)
    storage = get_storage(workflow_id)
    definition = storage.read_worker_call_args(node_location)

    if definition.logs_path is None:
        return PlainTextResponse("Node definition not found.")

    messages = ""

    with open(definition.logs_path, "rb") as fh:
        for line in fh:
            messages += line.decode()

    return PlainTextResponse(messages)
