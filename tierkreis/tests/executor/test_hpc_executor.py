from pathlib import Path
from uuid import UUID
import pytest
from tierkreis.builder import GraphBuilder
from tierkreis.controller import run_graph
from tierkreis.controller.data.graph import GraphData
from tierkreis.controller.data.location import Loc
from tierkreis.controller.data.models import TKR
from tierkreis.controller.data.types import ptype_from_bytes
from tierkreis.controller.executor.hpc.adapter import SLURM_EXECUTOR
from tierkreis.controller.executor.hpc.job_spec import (
    JobSpec,
    MpiSpec,
    ResourceSpec,
    UserSpec,
)
from tierkreis.controller.storage.filestorage import ControllerFileStorage

from tests.executor.stubs import mpi_rank_info


def mpi_graph() -> GraphData:
    builder = GraphBuilder(outputs_type=TKR[str | None])
    mpi_result = builder.task(mpi_rank_info())
    builder.outputs(mpi_result)
    return builder.data


def job_spec() -> JobSpec:
    return JobSpec(
        job_name="test_job",
        command="--allow-run-as-root /root/.local/bin/uv run slurm_mpi_worker/main.py ",
        user=UserSpec(
            account="test_usr",
        ),
        resource=ResourceSpec(nodes=2, memory_gb=None),
        walltime="00:15:00",
        mpi=MpiSpec(max_proc_per_node=1),
        error_path=Path("./error.log"),
        output_path=Path("./output.log"),
    )


@pytest.mark.skip(reason="Needs SLURM environment")
def test_slurm_with_mpi() -> None:
    g = mpi_graph()
    storage = ControllerFileStorage(
        UUID(int=22),
        name="mpi_graph",
        tierkreis_directory=Path("./infra/slurm_local/slurm_jobdir/checkpoints"),
    )
    executor = SLURM_EXECUTOR(
        spec=job_spec(),
        registry_path=Path("./infra/slurm_local/slurm_jobdir"),
        logs_path=storage.logs_path,
    )
    storage.clean_graph_files()
    run_graph(storage, executor, g, {})

    output_ports = g.nodes[g.output_idx()].inputs.keys()
    actual_output = {}
    for port in output_ports:
        actual_output[port] = ptype_from_bytes(storage.read_output(Loc(), port))

    assert "value" in actual_output
    assert actual_output["value"] is not None
