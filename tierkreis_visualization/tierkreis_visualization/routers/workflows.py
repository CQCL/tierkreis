import json
import logging
from typing import Any, assert_never
from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.websockets import WebSocket, WebSocketDisconnect

from tierkreis.controller.data.location import Loc, WorkerCallArgs
from tierkreis.exceptions import TierkreisError
from watchfiles import awatch  # type: ignore

from tierkreis_visualization.config import CONFIG, get_storage, templates
from tierkreis_visualization.data.eval import get_eval_node
from tierkreis_visualization.data.function import get_function_node
from tierkreis_visualization.data.loop import get_loop_node
from tierkreis_visualization.data.map import get_map_node
from tierkreis_visualization.data.workflows import get_workflows
from tierkreis_visualization.routers.models import PyGraph
from tierkreis_visualization.routers.navigation import breadcrumbs

router = APIRouter(prefix="/workflows")
logger = logging.getLogger(__name__)


# Update the routes section with this new route:
@router.websocket("/{workflow_id}/nodes/{node_location_str}")
async def websocket_endpoint(
    websocket: WebSocket, workflow_id: UUID, node_location_str: str
) -> None:
    try:
        await websocket.accept()
        # Handle WebSocket connection.
        await handle_websocket(websocket, workflow_id, node_location_str)
    except WebSocketDisconnect:
        pass


async def handle_websocket(
    websocket: WebSocket, workflow_id: UUID, node_location_str: str
) -> None:
    node_location = parse_node_location(node_location_str)
    # currently we are watching the entire workflow in the frontend
    node_path = CONFIG.tierkreis_path / str(workflow_id)
    async for _changes in awatch(node_path, recursive=True):
        ctx = get_node_data(workflow_id, node_location)
        await websocket.send_json(ctx)


@router.get("/")
def list_workflows(request: Request):
    workflows = get_workflows()
    return templates.TemplateResponse(
        request=request, name="workflows.html", context={"workflows": workflows}
    )


@router.get("/all")
def list_all_workflows(request: Request):
    workflows = get_workflows()
    return JSONResponse([workflow.model_dump(mode="json") for workflow in workflows])


class NodeResponse(BaseModel):
    definition: WorkerCallArgs


def parse_node_location(node_location_str: str) -> Loc:
    return Loc(node_location_str)


def get_errored_nodes(workflow_id: UUID) -> list[Loc]:
    storage = get_storage(workflow_id)
    errored_nodes = storage.read_errors(Loc("-"))
    return [parse_node_location(node) for node in errored_nodes.split("\n")]


def get_node_data(workflow_id: UUID, loc: Loc) -> dict[str, Any]:
    storage = get_storage(workflow_id)
    errored_nodes = get_errored_nodes(workflow_id)

    try:
        node = storage.read_node_def(loc)
    except FileNotFoundError:
        return {
            "breadcrumbs": breadcrumbs(workflow_id, loc),
            "url": f"/workflows/{workflow_id}/nodes/{loc}",
            "node_location": str(loc),
            "name": "unavailable.jinja",
        }

    ctx: dict[str, Any] = {}
    match node.type:
        case "eval":
            data = get_eval_node(storage, loc, errored_nodes)
            name = "eval.jinja"
            ctx = PyGraph(nodes=data.nodes, edges=data.edges).model_dump()

        case "loop":
            data = get_loop_node(storage, loc, errored_nodes)
            name = "loop.jinja"
            ctx = PyGraph(nodes=data.nodes, edges=data.edges).model_dump(
                by_alias=True, mode="json"
            )
        case "map":
            data = get_map_node(storage, loc, node, errored_nodes)
            name = "map.jinja"
            ctx = PyGraph(nodes=data.nodes, edges=data.edges).model_dump(
                by_alias=True, mode="json"
            )

        case "function":
            try:
                definition = storage.read_worker_call_args(loc)
            except FileNotFoundError:
                return {
                    "breadcrumbs": breadcrumbs(workflow_id, loc),
                    "url": f"/workflows/{workflow_id}/nodes/{loc}",
                    "node_location": str(loc),
                    "name": "unavailable.jinja",
                }
            data = get_function_node(storage, loc)
            name = "function.jinja"
            ctx = {
                "definition": definition.model_dump(mode="json"),
                "data": data.model_dump(mode="json"),
            }
        case "const" | "ifelse" | "eifelse" | "input" | "output":
            name = "fallback.jinja"
            parent = loc.parent()
            if parent is None:
                raise TierkreisError("Visualisable node should have parent.")

            inputs = {k: (parent.N(i), p) for k, (i, p) in node.inputs.items()}
            outputs = {k: (loc, k) for k in storage.read_output_ports(loc)}
            ctx = {"node": node, "inputs": inputs, "outputs": outputs}

        case _:
            assert_never(node)

    ctx["breadcrumbs"] = breadcrumbs(workflow_id, loc)
    ctx["url"] = f"/workflows/{workflow_id}/nodes/{loc}"
    ctx["node_location"] = str(loc)
    ctx["name"] = name

    return ctx


async def node_stream(workflow_id: UUID, node_location: Loc):
    node_path = CONFIG.tierkreis_path / str(workflow_id) / str(node_location)
    async for _changes in awatch(node_path, recursive=False):
        if (node_path / "definition").exists():
            ctx = get_node_data(workflow_id, node_location)
            yield f"event: message\ndata: {json.dumps(ctx)}\n\n"


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
    try:
        node_location = parse_node_location(node_location_str)
        storage = get_storage(workflow_id)
        definition = storage.read_worker_call_args(node_location)

        with open(definition.inputs[port_name], "rb") as fh:
            return JSONResponse(json.loads(fh.read()))
    except FileNotFoundError as e:
        return PlainTextResponse(str(e))


@router.get("/{workflow_id}/nodes/{node_location_str}/outputs/{port_name}")
def get_output(workflow_id: UUID, node_location_str: str, port_name: str):
    output_file = (
        CONFIG.tierkreis_path
        / str(workflow_id)
        / node_location_str
        / "outputs"
        / port_name
    )
    try:
        with open(output_file, "rb") as fh:
            return JSONResponse(json.loads(fh.read()))
    except FileNotFoundError as e:
        return PlainTextResponse(str(e))


@router.get("/{workflow_id}/nodes/{node_location_str}/logs")
def get_function_logs(workflow_id: UUID, node_location_str: str) -> PlainTextResponse:
    node_location = parse_node_location(node_location_str)
    storage = get_storage(workflow_id)
    try:
        definition = storage.read_node_def(node_location)
    except (FileNotFoundError, TierkreisError):
        return PlainTextResponse("Node definition not found; node is not started.")
    if definition.type != "function":
        return PlainTextResponse("Only function nodes should have a log file.")
    try:
        call_args = storage.read_worker_call_args(node_location)
    except (FileNotFoundError, TierkreisError):
        logger.warning("Function node has no valid call args.")
        return PlainTextResponse("No logfile found")
    if call_args.logs_path is None or not call_args.logs_path.exists():
        return PlainTextResponse("No logfile found")

    messages = ""
    with open(call_args.logs_path, "rb") as fh:
        for line in fh:
            messages += line.decode()

    return PlainTextResponse(messages)


@router.get("/{workflow_id}/logs")
def get_logs(workflow_id: UUID) -> PlainTextResponse:
    storage = get_storage(workflow_id)
    if not storage.logs_path.is_file():
        return PlainTextResponse("Logfile not found.")

    messages = ""
    with open(storage.logs_path, "rb") as fh:
        for line in fh:
            messages += line.decode()

    return PlainTextResponse(messages)


@router.get("/{workflow_id}/nodes/{node_location_str}/errors")
def get_errors(workflow_id: UUID, node_location_str: str):
    node_location = parse_node_location(node_location_str)
    storage = get_storage(workflow_id)
    if not storage.node_has_error(node_location):
        return PlainTextResponse("Node has no errors.", status_code=404)

    messages = storage.read_errors(node_location)
    return PlainTextResponse(messages)
