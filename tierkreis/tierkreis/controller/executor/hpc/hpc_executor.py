import logging
import subprocess
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Callable, Protocol

from tierkreis.controller.executor.hpc.job_spec import JobSpec
from tierkreis.exceptions import TierkreisError

logger = logging.getLogger(__name__)


class HPCExecutor(Protocol):
    launchers_path: Path | None
    logs_path: Path
    errors_path: Path
    spec: JobSpec
    script_fn: Callable[[JobSpec], str]
    command: str


def generate_script(
    template_fn: Callable[[JobSpec], str], spec: JobSpec, path: Path
) -> None:
    with open(path, "w+", encoding="utf-8") as fh:
        fh.write(template_fn(spec))


def run_hpc_executor(
    executor: HPCExecutor, launcher_name: str, worker_call_args_path: Path
) -> None:
    logging.basicConfig(
        format="%(asctime)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
        filename=executor.logs_path,
        filemode="a",
        level=logging.INFO,
        force=True,
    )
    logger.info("START %s %s", launcher_name, worker_call_args_path)

    if executor.launchers_path:
        executor.spec.command = (
            f"cd {executor.launchers_path}/{launcher_name} && {executor.spec.command}"
        )

    executor.spec.command += " " + str(worker_call_args_path)
    submission_cmd = [executor.command]
    if executor.spec.output_path is None:
        submission_cmd += ["-o", str(executor.logs_path)]
    else:
        submission_cmd += ["-o", str(executor.spec.output_path)]
    if executor.spec.error_path is None:
        submission_cmd += ["-e", str(executor.errors_path)]
    else:
        submission_cmd += ["-e", str(executor.spec.error_path)]
    if executor.spec.include_no_check_directory_flag:
        submission_cmd += ["--no-check-directory"]

    with NamedTemporaryFile(
        mode="w+",
        delete=True,
        suffix=".sh",
        prefix=f"{executor.spec.job_name}-",
    ) as script_file:
        generate_script(executor.script_fn, executor.spec, Path(script_file.name))
        submission_cmd.append(script_file.name)

        process = subprocess.run(
            submission_cmd,
            start_new_session=True,
            capture_output=True,
            universal_newlines=True,
        )
    if process.returncode != 0:
        with open(executor.errors_path, "a") as efh:
            breakpoint()
            efh.write("Error from script")
            efh.write(process.stderr)
        raise TierkreisError(f"Executor failed with return code {process.returncode}")
    logger.info("Submitted job with return code %s", process.stdout.rstrip())
