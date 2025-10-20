import json
import logging
import shutil
import subprocess
from pathlib import Path

from tierkreis.consts import TKR_DIR_KEY
from tierkreis.controller.data.location import WorkerCallArgs
from tierkreis.controller.executor.environment import create_env
from tierkreis.exceptions import TierkreisError

logger = logging.getLogger(__name__)


class UvExecutor:
    """Executes workers in an UV python environment.

    Implements: :py:class:`tierkreis.controller.executor.protocol.ControllerExecutor`
    """

    def __init__(
        self, registry_path: Path, logs_path: Path, env: dict[str, str] | None = None
    ) -> None:
        self.launchers_path = registry_path
        self.logs_path = logs_path
        self.errors_path = logs_path
        self.env = env or {}

    def run(
        self,
        launcher_name: str,
        worker_call_args_path: Path,
        uv_path: str | None = None,
    ) -> None:
        logging.basicConfig(
            format="%(asctime)s: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
            filename=self.logs_path,
            filemode="a",
            level=logging.INFO,
        )
        self.errors_path = (
            self.logs_path.parent.parent / worker_call_args_path.parent / "errors"
        )
        logger.info("START %s %s", launcher_name, worker_call_args_path)

        if uv_path is None:
            uv_path = shutil.which("uv")
        if uv_path is None:
            raise TierkreisError("uv is required to use the uv_executor")

        with open(self.logs_path.parent.parent / worker_call_args_path) as fh:
            call_args = WorkerCallArgs(**json.load(fh))

        worker_path = self.launchers_path / launcher_name

        env = self.env.copy()
        env.update(create_env(call_args, self.logs_path.parent, False))
        env["worker_call_args_file"] = str(
            self.logs_path.parent / worker_call_args_path
        )
        if "VIRTUAL_ENVIRONMENT" not in env:
            env["VIRTUAL_ENVIRONMENT"] = ""
        if TKR_DIR_KEY not in env:
            env[TKR_DIR_KEY] = str(self.logs_path.parent.parent)
        _error_path = self.errors_path.parent / "_error"

        with open(self.logs_path, "a") as lfh:
            with open(self.errors_path, "a") as efh:
                proc = subprocess.Popen(
                    ["bash"],
                    start_new_session=True,
                    stdin=subprocess.PIPE,
                    stderr=efh,
                    stdout=lfh,
                    cwd=worker_path,
                    env=env,
                )
                proc.communicate(
                    f"({uv_path} run main.py {worker_call_args_path} || touch {_error_path}) &".encode(),
                    timeout=10,
                )
