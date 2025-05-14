import logging
import os
from datetime import datetime
from pathlib import Path
from sys import argv

from pydantic import BaseModel
from tierkreis.worker import Worker

import qnexus as qnx
from dotenv import load_dotenv
from pytket._tket.circuit import Circuit
from pytket.backends.backendresult import BackendResult
from pytket.backends.status import StatusEnum
from qnexus.client.utils import write_token
from qnexus.exceptions import ResourceFetchFailed
from qnexus.models import QuantinuumConfig
from qnexus.models.references import ExecuteJobRef, ExecutionProgram
from time import sleep

logger = logging.getLogger(__name__)
load_dotenv()

worker = Worker("nexus_worker")


def setup_project():
    refresh_token = os.environ.get("NEXUS_REFRESH_TOKEN")
    assert refresh_token is not None
    write_token("refresh_token", refresh_token)


def _check_status(job_ref: ExecuteJobRef, delay: int) -> StatusEnum:
    setup_project()
    sleep(delay)
    try:
        return qnx.jobs.status(job_ref).status
    except ResourceFetchFailed as exc:
        print(exc)
        return StatusEnum.SUBMITTED


def execute_circuits(
    list_circ: list[Circuit], n_shots: int, backend_name: str, project_name: str
) -> ExecuteJobRef:
    """upload, compile, and execute circuits"""
    setup_project()
    my_project_ref = qnx.projects.get_or_create(name=project_name)
    qnx.context.set_active_project(my_project_ref)

    my_circuit_refs: list[ExecutionProgram] = []
    for circ in list_circ:
        my_circuit_refs.append(
            qnx.circuits.upload(
                name=f"My Circuit from {datetime.now()}",
                circuit=circ,
                project=my_project_ref,
            )
        )

    execute_job_ref = qnx.start_execute_job(
        circuits=my_circuit_refs,
        name=f"My Execute Job from {datetime.now()}",
        n_shots=[n_shots] * len(my_circuit_refs),
        backend_config=QuantinuumConfig(device_name="reimei-E"),
        project=my_project_ref,
    )
    return execute_job_ref


def get_backend_results(execute_job_ref: ExecuteJobRef) -> list[BackendResult]:
    "make list of backend results form execute_job_ref"
    setup_project()
    execute_job_result_refs = qnx.jobs.results(execute_job_ref)
    backend_results: list[BackendResult] = []
    for i in range(len(execute_job_result_refs)):
        result = execute_job_result_refs[i].download_result()
        assert isinstance(result, BackendResult)
        backend_results.append(result)
    return backend_results


class SubmitResult(BaseModel):
    execute_ref: dict


@worker.function()
def submit(circuits: dict, n_shots: int) -> SubmitResult:
    pytket_circuits = [Circuit.from_dict(x) for x in circuits]

    execute_ref = execute_circuits(
        pytket_circuits,
        n_shots=n_shots,
        backend_name="H1-1LE",
        project_name="Riken-Test",
    )

    return SubmitResult(execute_ref=execute_ref.model_dump())


class StatusResult(BaseModel):
    status_enum: str


@worker.function()
def check_status(execute_ref: dict) -> StatusResult:
    ref = ExecuteJobRef(**execute_ref)
    status_enum = _check_status(ref, 30)
    return StatusResult(status_enum=status_enum.name)


class BackendResults(BaseModel):
    backend_results: list[dict]


@worker.function()
def get_results(execute_ref: dict) -> BackendResults:
    ref = ExecuteJobRef(**execute_ref)
    results = get_backend_results(ref)
    return BackendResults(backend_results=[x.to_dict() for x in results])


def main() -> None:
    node_definition_path = argv[1]
    worker.run(Path(node_definition_path))


if __name__ == "__main__":
    main()
