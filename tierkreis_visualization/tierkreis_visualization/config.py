from pathlib import Path

from pydantic_settings import BaseSettings
from starlette.templating import Jinja2Templates


class Settings(BaseSettings):
    tierkreis_path: Path = Path.home() / ".tierkreis" / "checkpoints"


CONFIG = Settings()
CONFIG.tierkreis_path.mkdir(parents=True, exist_ok=True)
templates = Jinja2Templates(directory=(Path(__file__).parent / "templates").absolute())
