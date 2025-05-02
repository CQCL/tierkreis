from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from tierkreis_visualization.config import templates
from tierkreis_visualization.routers.workflows import router as workflows_router

app = FastAPI()

app.include_router(workflows_router)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def read_root(request: Request):
    return RedirectResponse(url="/workflows")
