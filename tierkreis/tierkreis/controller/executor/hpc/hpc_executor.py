import logging
import subprocess
from pathlib import Path
from tempfile import NamedTemporaryFile

from tierkreis.controller.executor.hpc.job_spec import JobSpec
from tierkreis.controller.executor.hpc.protocol import HpcAdapter
from tierkreis.exceptions import TierkreisError

logger = logging.getLogger(__name__)


class HpcExecutor:
    def __init__(
        self, registry_path: Path, logs_path: Path, adapter: HpcAdapter, spec: JobSpec
    ) -> None:
        self.launchers_path = registry_path
        self.logs_path = logs_path
        self.errors_path = logs_path
        self.spec = spec
        self.adapter = adapter

    def run(self, launcher_name: str, node_definition_path: Path) -> None:
        launcher_path = self.launchers_path / launcher_name
        self.errors_path = node_definition_path.parent / "errors"

        self.spec.error_path = self.errors_path
        self.spec.output_path = self.logs_path

        logging.basicConfig(
            format="%(asctime)s: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
            filename=self.logs_path,
            filemode="a",
            level=logging.INFO,
        )
        logger.info("START %s %s", launcher_name, node_definition_path)

        with NamedTemporaryFile(
            mode="w",
            delete=False,
            dir=launcher_path,
            suffix=".sh",
            prefix=f"{self.spec.job_name}-",
        ) as script_file:
            self.adapter.generate_script(self.spec, Path(script_file.name))
            submission_cmd = [self.adapter.command, script_file.name]
            # todo: additional input

            with open(self.logs_path, "a") as lfh:
                with open(self.errors_path, "a") as efh:
                    process = subprocess.run(
                        submission_cmd,
                        cwd=launcher_path,
                        env=self.spec.environment,  # could be export in bash script?
                        start_new_session=True,
                        capture_output=True,
                        universal_newlines=True,
                        stderr=efh,
                        stdout=lfh,
                    )
                    if process.returncode != 0:
                        with open(self.errors_path, "a") as efh:
                            efh.write("Error from script")
                            efh.write(process.stderr)
                        raise TierkreisError(
                            f"Executor failed with return code {process.returncode}"
                        )
                    logger.info(
                        "Submitted job with return code %d", process.stdout.rstrip()
                    )
