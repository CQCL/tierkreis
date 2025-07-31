from datetime import datetime
import os
from uuid import UUID

from pydantic import BaseModel
from tierkreis.controller.data.location import Loc
from tierkreis_visualization.config import CONFIG, get_storage


class WorkflowDisplay(BaseModel):
    id: UUID
    id_int: int
    name: str | None
    start: str


def get_workflows() -> list[WorkflowDisplay]:
    folders = os.listdir(CONFIG.tierkreis_path)
    folders.sort()
    workflows: list[WorkflowDisplay] = []
    for folder in folders:
        try:
            id = UUID(folder)
            metadata = get_storage(id).read_metadata(Loc(""))
            name = metadata["name"] or "workflow"
            start = metadata.get("start", str(datetime.now()))
            workflows.append(
                WorkflowDisplay(id=id, id_int=int(id), name=name, start=start)
            )
        except (TypeError, ValueError):
            continue

    return workflows
