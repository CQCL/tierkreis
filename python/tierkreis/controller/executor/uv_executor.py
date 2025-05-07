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
        self.errors_path = logs_path

    def run(
        self,
        launcher_name: str,
        node_definition_path: Path,
        uv_path: str | None = None,
    ) -> None:
        logging.basicConfig(
            format="%(asctime)s: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
            filename=self.logs_path,
            filemode="a",
            level=logging.INFO,
        )
        self.errors_path = node_definition_path.parent / "errors"
        logger.info("START %s %s", launcher_name, node_definition_path)

        if uv_path is None:
            uv_path = shutil.which("uv")
        if uv_path is None:
            raise TierkreisError("uv is required to use the uv_executor")

        worker_path = self.launchers_path / launcher_name
        env = {"VIRTUAL_ENVIRONMENT": ""}

        with open(self.logs_path, "a") as lfh:
            with open(self.errors_path, "a") as efh:
                subprocess.Popen(
                    [uv_path, "run", "main.py", node_definition_path],
                    start_new_session=True,
                    cwd=worker_path,
                    stderr=efh,
                    stdout=lfh,
                    env=env,
                )
