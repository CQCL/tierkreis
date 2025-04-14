from asyncio import sleep
import json
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from starlette.responses import JSONResponse, PlainTextResponse
from tierkreis.controller.data.location import NodeLocation, NodeDefinition
from tierkreis.controller.storage.filestorage import ControllerFileStorage
from tierkreis.controller.storage.protocol import ControllerStorage

from tierkreis_visualization.config import CONFIG, templates
from tierkreis_visualization.data.eval import get_eval_node
from tierkreis_visualization.data.loop import get_loop_node
from tierkreis_visualization.data.workflows import get_workflows
from tierkreis_visualization.routers.models import JSGraph
from tierkreis_visualization.routers.navigation import breadcrumbs

router = APIRouter(prefix="/workflows")


@router.get("/")
def list_workflows(request: Request):
    workflows = get_workflows()
    return templates.TemplateResponse(
        request=request, name="workflows.html", context={"workflows": workflows}
    )


class NodeResponse(BaseModel):
    definition: NodeDefinition


def parse_node_location(node_location_str: str) -> NodeLocation:
    if node_location_str.startswith("-"):
        node_location_str = node_location_str[1:]
    if node_location_str.startswith("."):
        node_location_str = node_location_str[1:]

    return NodeLocation.from_str(node_location_str)


def get_storage(workflow_id: UUID) -> ControllerStorage:
    return ControllerFileStorage(
        workflow_id=workflow_id, tierkreis_directory=CONFIG.tierkreis_path
    )


def get_node_data(workflow_id: UUID, node_location: NodeLocation) -> dict[str, Any]:
    storage = get_storage(workflow_id)

    definition = storage.read_node_definition(node_location)
    function_name = definition.function_name

    if function_name == "eval":
        data = get_eval_node(storage, node_location)
        name = "eval.html"
        ctx: dict[str, Any] = JSGraph.from_python(data.nodes, data.edges).model_dump(
            by_alias=True
        )

    elif function_name == "loop":
        data = get_loop_node(storage, node_location)
        name = "loop.html"
        ctx = JSGraph.from_python(data.nodes, data.edges).model_dump(by_alias=True)

    else:
        name = "fallback.html"
        ctx = {"definition": definition.model_dump()}

    ctx["breadcrumbs"] = breadcrumbs(workflow_id, node_location)
    ctx["url"] = f"/workflows/{workflow_id}/nodes/-{node_location}"
    ctx["node_location"] = str(node_location)
    ctx["name"] = name

    return ctx


async def node_stream(workflow_id: UUID, node_location: NodeLocation):
    metadata_path = (
        CONFIG.tierkreis_path / str(workflow_id) / str(node_location) / "_metadata"
    )
    mtime = 0
    for _ in range(100):
        new_mtime = metadata_path.stat().st_mtime
        if new_mtime > mtime:
            mtime = new_mtime
            ctx = get_node_data(workflow_id, node_location)
            yield f"event: message\ndata: {json.dumps(ctx)}\n\n"
        await sleep(0.5)


@router.get("/{workflow_id}/nodes/{node_location_str}")
def get_node(request: Request, workflow_id: UUID, node_location_str: str):
    node_location = parse_node_location(node_location_str)
    ctx = get_node_data(workflow_id, node_location)
    if request.headers["Accept"] == "application/json":
        return JSONResponse(ctx)

    if request.headers["Accept"] == "text/event-stream":
        return StreamingResponse(
            node_stream(workflow_id, node_location), media_type="text/event-stream"
        )

    return templates.TemplateResponse(request=request, name=ctx["name"], context=ctx)


@router.get("/{workflow_id}/nodes/{node_location_str}/inputs/{port_name}")
def get_input(workflow_id: UUID, node_location_str: str, port_name: str):
    node_location = parse_node_location(node_location_str)
    storage = get_storage(workflow_id)
    definition = storage.read_node_definition(node_location)

    with open(definition.inputs[port_name], "rb") as fh:
        return JSONResponse(json.loads(fh.read()))


@router.get("/{workflow_id}/nodes/{node_location_str}/outputs/{port_name}")
def get_output(workflow_id: UUID, node_location_str: str, port_name: str):
    node_location = parse_node_location(node_location_str)
    storage = get_storage(workflow_id)
    definition = storage.read_node_definition(node_location)

    with open(definition.outputs[port_name], "rb") as fh:
        return JSONResponse(json.loads(fh.read()))


@router.get("/{workflow_id}/nodes/{node_location_str}/logs")
def get_logs(workflow_id: UUID, node_location_str: str):
    node_location = parse_node_location(node_location_str)
    storage = get_storage(workflow_id)
    definition = storage.read_node_definition(node_location)

    if definition.logs_path is None:
        return PlainTextResponse("Node definition not found.")

    messages = ""

    with open(definition.logs_path, "rb") as fh:
        for line in fh:
            messages += line.decode()

    return PlainTextResponse(messages)
