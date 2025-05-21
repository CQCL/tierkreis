import json
from pathlib import Path
from typing import Any, assert_never
from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from starlette.responses import JSONResponse, PlainTextResponse
from tierkreis.controller.data.location import Loc, WorkerCallArgs
from tierkreis.controller.storage.adjacency import in_edges
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


@router.get("/")
def list_workflows(request: Request):
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


def get_node_data(workflow_id: UUID, loc: Loc) -> dict[str, Any]:
    storage = get_storage(workflow_id)
    errored_nodes = get_errored_nodes(workflow_id)
    node = storage.read_node_def(loc)
    ctx: dict[str, Any] = {}

    match node.type:
        case "eval":
            data = get_eval_node(storage, loc, errored_nodes)
            name = "eval.jinja"
            ctx = PyGraph(nodes=data.nodes, edges=data.edges).model_dump()

        case "loop":
            data = get_loop_node(storage, loc, errored_nodes)
            name = "loop.jinja"
            ctx = PyGraph(nodes=data.nodes, edges=data.edges).model_dump()

        case "map":
            data = get_map_node(storage, loc, node, errored_nodes)
            name = "map.jinja"
            ctx = PyGraph(nodes=data.nodes, edges=data.edges).model_dump()

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
            ctx = {"definition": definition.model_dump(), "data": data}

        case "const" | "input" | "output" | "ifelse" | "eifelse":
            name = "fallback.html"
            parent = loc.parent()
            if parent is None:
                raise TierkreisError("Any visualisable node should have a parent.")

            inputs = {k: (parent.N(i), p) for k, (i, p) in in_edges(node).items()}
            outputs = {k: (loc, k) for k in storage.read_output_ports(loc)}
            print(inputs.items())
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


@router.get("/{workflow_id}/nodes/{node_location_str}/outputs/{port_name}")
def get_output(workflow_id: UUID, node_location_str: str, port_name: str):
    loc = parse_node_location(node_location_str)
    output_path = CONFIG.tierkreis_path / str(workflow_id) / loc / "outputs" / port_name
    with open(output_path, "rb") as fh:
        return JSONResponse(json.loads(fh.read()))


@router.get("/{workflow_id}/nodes/{node_location_str}/logs")
def get_logs(workflow_id: UUID, node_location_str: str):
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
