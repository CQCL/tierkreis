from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    tkr_dir: Path = Path.home() / ".tierkreis"


CONFIG = Settings()
