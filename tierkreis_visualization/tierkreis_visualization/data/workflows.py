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
    start_time: str


def get_workflows() -> list[WorkflowDisplay]:
    storage_type = os.environ.get("TKR_STORAGE", "FileStorage")
    if storage_type == "GraphDataStorage":
        return [
            WorkflowDisplay(
                id=UUID(int=0),
                id_int=0,
                name="tmp",
                start_time=datetime.now().isoformat(),
            )
        ]
    return get_workflows_from_disk()


def get_workflows_from_disk() -> list[WorkflowDisplay]:
    folders = os.listdir(CONFIG.tierkreis_path)
    folders.sort()
    workflows: list[WorkflowDisplay] = []
    for folder in folders:
        try:
            id = UUID(folder)
            metadata = get_storage(id).read_metadata(Loc(""))
            name = metadata["name"] or "workflow"
            start = metadata.get("start_time", datetime.now().isoformat())
            workflows.append(
                WorkflowDisplay(id=id, id_int=int(id), name=name, start_time=start)
            )
        except (TypeError, ValueError):
            continue

    return workflows
