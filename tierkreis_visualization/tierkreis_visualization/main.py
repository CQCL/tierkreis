from fastapi import FastAPI, Request

from tierkreis_visualization.config import templates
from tierkreis_visualization.routers.workflows import router as workflows_router

app = FastAPI()

app.include_router(workflows_router)


@app.get("/")
def read_root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")
