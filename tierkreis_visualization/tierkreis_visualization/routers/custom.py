from fastapi import APIRouter, Request
from watchfiles import awatch
from tierkreis_visualization.config import templates
from tierkreis_visualization.data.workflows import get_workflows

router = APIRouter()

@router.post("/jsgraphs")
def save_jsgraph(request: Request):
    print(request)
    # save jsgraph to disk
    return "ok"




