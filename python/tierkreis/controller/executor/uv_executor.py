import logging
import shutil
import subprocess
from pathlib import Path

from tierkreis.exceptions import TierkreisError

logger = logging.getLogger(__name__)


class UvExecutor:
    def __init__(self, registry_path: Path, logs_path: Path) -> None:
        self.launchers_path = registry_path
        self.logs_path = logs_path

    def run(self, launcher_name: str, node_definition_path: Path) -> None:
        logging.basicConfig(
            format="%(asctime)s: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
            filename=self.logs_path,
            filemode="a",
            level=logging.INFO,
        )
        logger.info("START %s %s", launcher_name, node_definition_path)

        uv_path = shutil.which("uv")
        if uv_path is None:
            raise TierkreisError("uv is required to use the uv_executor")
        worker_path = self.launchers_path / launcher_name
        env = {"VIRTUAL_ENVIRONMENT": ""}

        with open(self.logs_path, "a") as fh:
            subprocess.Popen(
                [uv_path, "run", "main.py", node_definition_path],
                start_new_session=True,
                cwd=worker_path,
                stderr=fh,
                stdout=fh,
                env=env,
            )
