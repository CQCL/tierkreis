import os
from uuid import UUID

from tierkreis_visualization.config import CONFIG


def get_workflows():
    folders = os.listdir(CONFIG.tierkreis_path)
    workflow_ids: list[UUID] = []
    for folder in folders:
        try:
            workflow_id = UUID(folder)
            workflow_ids.append(workflow_id)
        except (TypeError, ValueError):
            continue

    return workflow_ids
