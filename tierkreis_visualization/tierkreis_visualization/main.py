from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware


from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import uvicorn

from tierkreis_visualization.routers.workflows import router as workflows_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8000",
        "http://localhost:5137",
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
    uvicorn.run(app)
