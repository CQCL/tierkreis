import shutil
from pathlib import Path

from tierkreis.controller.executor.hpc_executor import HPCExecutor
from tierkreis.controller.executor.multiple import MultipleExecutor
from tierkreis.controller.executor.protocol import ControllerExecutor


def _executor(registry_path: Path, logs_path: Path) -> HPCExecutor:
    uv_path = shutil.which("uv")
    if not uv_path:
        raise ValueError("uv not found")
    executor = HPCExecutor(
        registry_path=registry_path,
        logs_path=logs_path,
        command="pjsub",
        working_directory=(Path(__file__).parent / "..").resolve(),
        additional_input=uv_path + " run main.py",
    )

    executor.add_flags_from_config_file(Path("./default_flags"))
    return executor


def small_executor(registry_path: Path, logs_path: Path) -> HPCExecutor:
    arch = "aarch64"
    executor = _executor(registry_path, logs_path)
    executor.add_flags(
        [
            "-L node=1",
            "-L elapse=15:00",
            f"-x UV_PROJECT_ENVIRONMENT=venv_{arch}",
            "--llio sharedtmp-size=10Gi",
        ]
    )
    return executor


def large_executor(registry_path: Path, logs_path: Path) -> HPCExecutor:
    arch = "aarch64"
    executor = _executor(registry_path, logs_path)
    executor.add_flags(
        [
            "-L node=32",
            "-L elapse=3:00:00",
            f"-x UV_PROJECT_ENVIRONMENT=venv_{arch}",
            "--llio sharedtmp-size=64Gi",
            "-x PJM_LLIO_GFSCACHE=/vol0004",
        ]
    )
    return executor


def pjsub_executor(registry_path: Path, logs_path: Path) -> ControllerExecutor:
    s_executor = small_executor(registry_path, logs_path)
    l_executor = large_executor(registry_path, logs_path)
    executor = MultipleExecutor(
        s_executor,
        {"small": s_executor, "large": l_executor},
        {"small": "some_nodes", "large": "other_nodes"},
    )
    return executor
