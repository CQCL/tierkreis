from pathlib import Path
from uuid import UUID

from tierkreis_visualization.data.workflows import StorageType
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from tierkreis.controller.data.graph import GraphData
from tierkreis.controller.storage.graphdata import GraphDataStorage
from tierkreis.controller.storage.protocol import ControllerStorage
from tierkreis_visualization.config import CONFIG, get_storage
from tierkreis_visualization.routers.workflows import router as workflows_router


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8000",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://localhost:5173",
    ],  # Adjust as necessary
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(workflows_router)
app.mount(
    "/static",
    StaticFiles(directory=(Path(__file__).parent / "static").absolute()),
    name="static",
)


@app.get("/")
def read_root(request: Request):
    return RedirectResponse(url="/static/dist/index.html")


def start() -> None:
    workflow_path = CONFIG.tierkreis_path / str(UUID(int=0))
    if workflow_path.exists() and workflow_path.is_dir():
        workflow_path.rmdir()
    app.state.get_storage_fn = get_storage
    app.state.storage_type = StorageType.FILESTORAGE
    uvicorn.run(app)


def visualize_graph(
    graph: GraphData,
    storage: ControllerStorage | None = None,
) -> None:
    """Visualize a computation graph in a web browser.

    :param graph: The computation graph to visualize.
    :type graph: GraphData
    :param storage: The storage backend to use for the visualization.
    :type storage: ControllerStorage | None. Defaults to GraphDataStorage.
    """
    if storage is None:
        storage = GraphDataStorage(UUID(int=0), graph=graph)

    def get_storage(workflow_id: UUID) -> ControllerStorage:
        return storage

    app.state.get_storage_fn = get_storage
    app.state.storage_type = StorageType.GRAPHDATA
    uvicorn.run(app)


if __name__ == "__main__":
    start()
