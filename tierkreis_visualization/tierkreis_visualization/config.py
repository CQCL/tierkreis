from pathlib import Path
from uuid import UUID

from pydantic_settings import BaseSettings
from starlette.templating import Jinja2Templates
from tierkreis.controller.storage.protocol import ControllerStorage
from tierkreis.controller.storage.filestorage import ControllerFileStorage


class Settings(BaseSettings):
    tierkreis_path: Path = Path.home() / ".tierkreis" / "checkpoints"


CONFIG = Settings()

CONFIG.tierkreis_path.mkdir(parents=True, exist_ok=True)

templates = Jinja2Templates(
    directory=(Path(__file__).parent.parent / "templates").absolute()
)


def get_storage(workflow_id: UUID) -> ControllerStorage:
    return ControllerFileStorage(
        workflow_id=workflow_id, tierkreis_directory=CONFIG.tierkreis_path
    )
