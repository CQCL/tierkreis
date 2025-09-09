from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    checkpoints_dir: Path = Path.home() / ".tierkreis" / "checkpoints"


CONFIG = Settings()
