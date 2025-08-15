from pathlib import Path
import platform
from pydantic import BaseModel, Field


class JobSpec(BaseModel):
    job_name: str
    command: str  # used instead of popen.input
    nodes: int = 1
    cores_per_node: int | None = 1
    memory_gb: int | None = 4
    walltime: str = "01:00:00"  # HH:MM:SS Replacement?
    queue: str | None = None
    account: str | None = None  # resource group(pjsub), project account etc
    output_path: Path | None = None
    error_path: Path | None = None
    extra_scheduler_args: dict[str, str | None] = Field(default_factory=dict)
    environment: dict[str, str] = Field(default_factory=dict)


def pjsub_large_spec() -> JobSpec:
    arch = platform.machine()
    uv_path = Path.home() / ".local" / f"bin_{arch}" / "uv"
    return JobSpec(
        job_name="pjsub_large",
        command=f"{str(uv_path)} run main.py",
        queue="q-QTM-M",
        account="hp240496",
        nodes=32,
        environment={
            "VIRTUAL_ENVIRONMENT": "",
            "UV_PROJECT_ENVIRONMENT": f"venv_{arch}",
            "PJM_LLIO_GFSCACHE": "/vol0004",
        },
        walltime="03:00:00",
        extra_scheduler_args={
            "--no-check-directory": None,
            "--mpi": "max-proc-per-node=4",
            "-z": "jid",
            "--llio": "sharedtmp-size=64Gi",
        },
    )


def pjsub_small_spec() -> JobSpec:
    arch = platform.machine()
    uv_path = Path.home() / ".local" / f"bin_{arch}" / "uv"
    return JobSpec(
        job_name="pjsub_small",
        command=f"{str(uv_path)} run main.py",
        account="hp240496",
        nodes=1,
        environment={
            "VIRTUAL_ENVIRONMENT": "",
            "UV_PROJECT_ENVIRONMENT": f"venv_{arch}",
        },
        walltime="00:15:00",
        extra_scheduler_args={
            "--no-check-directory": None,
            "--mpi": "max-proc-per-node=4",
            "-z": "jid",
            "--llio": "sharedtmp-size=10Gi",
        },
    )
