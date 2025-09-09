from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    tkr_checkpoints: Path = Path.home() / ".tierkreis" / "checkpoints"


CONFIG = Settings()
