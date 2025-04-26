from pathlib import Path

from pydantic_settings import BaseSettings
from starlette.templating import Jinja2Templates


class Settings(BaseSettings):
    tierkreis_path: Path = Path.home() / ".tierkreis" / "checkpoints"


CONFIG = Settings()

assert CONFIG.tierkreis_path.exists()

templates = Jinja2Templates(directory="templates")
