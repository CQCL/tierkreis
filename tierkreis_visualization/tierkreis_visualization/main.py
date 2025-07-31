from pathlib import Path
from typing import Callable
from uuid import UUID
from fastapi.middleware.cors import CORSMiddleware


from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from tierkreis.controller.storage.protocol import ControllerStorage
from tierkreis_visualization.config import get_storage
import uvicorn

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


def start():
    app.state.get_storage_fn = get_storage
    uvicorn.run(app, reload=True)


def start_with_storage_fn(get_storage_fn: Callable[[UUID], ControllerStorage]):
    app.state.get_storage_fn = get_storage_fn
    uvicorn.run(app)


if __name__ == "__main__":
    start()
