import os
from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel

from tierkreis.controller.data.location import Loc
from tierkreis.controller.storage.filestorage import ControllerFileStorage
from tierkreis.controller.storage.graphdata import GraphDataStorage
from tierkreis_visualization.config import CONFIG, get_storage


class StorageType(Enum):
    FILESTORAGE = ControllerFileStorage
    GRAPHDATA = GraphDataStorage


class WorkflowDisplay(BaseModel):
    id: UUID
    id_int: int
    name: str | None
    start_time: str


def get_workflows(storage_type: StorageType) -> list[WorkflowDisplay]:
    if storage_type == StorageType.GRAPHDATA:
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
