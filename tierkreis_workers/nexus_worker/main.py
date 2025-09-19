import logging
from datetime import datetime
from sys import argv
from tierkreis import Worker

import qnexus as qnx
from pytket._tket.circuit import Circuit
from pytket.backends.backendresult import BackendResult
from pytket.backends.status import StatusEnum
from qnexus.exceptions import ResourceFetchFailed
from qnexus.models import QuantinuumConfig
from qnexus.models.references import ExecuteJobRef, ExecutionProgram
from time import sleep

logger = logging.getLogger(__name__)
worker = Worker("nexus_worker")


@worker.task()
def upload_circuit(project_name: str, circ: Circuit) -> ExecutionProgram:
    """Wrapper around `qnx.circuits.upload`."""

    my_project_ref = qnx.projects.get_or_create(name=project_name)
    circuit_name = circ.name if circ.name else f"circuit_{datetime.now()}"
    qnx.context.set_active_project(my_project_ref)
    return qnx.circuits.upload(name=circuit_name, circuit=circ, project=my_project_ref)


@worker.task()
def start_execute_job(
    project_name: str,
    job_name: str,
    circuits: list[ExecutionProgram],
    n_shots: list[int],
    backend_config: qnx.BackendConfig,
) -> ExecuteJobRef:
    "Wrapper around `qnx.start_execute_job`."

    my_project_ref = qnx.projects.get_or_create(name=project_name)
    qnx.context.set_active_project(my_project_ref)
    return qnx.start_execute_job(circuits, n_shots, backend_config, job_name)


@worker.task()
def status(execute_ref: ExecuteJobRef) -> str:
    """Wrapper around `qnx.jobs.status`."""

    try:
        return str(qnx.jobs.status(execute_ref).status)
    except ResourceFetchFailed as exc:
        print(exc)
        return str(StatusEnum.SUBMITTED)


@worker.task()
def get_results(execute_ref: ExecuteJobRef) -> list[BackendResult]:
    """Wrapper around `qnx.results` and `qnx.download_result`."""

    execute_job_result_refs = qnx.jobs.results(execute_ref)
    backend_results: list[BackendResult] = []
    for i in range(len(execute_job_result_refs)):
        result = execute_job_result_refs[i].download_result()
        assert isinstance(result, BackendResult)
        backend_results.append(result)
    return backend_results


## DEPRECATED TASKS ##


@worker.task()
def check_status(execute_ref: ExecuteJobRef) -> str:
    sleep(30)
    try:
        return str(qnx.jobs.status(execute_ref).status)
    except ResourceFetchFailed as exc:
        print(exc)
        return str(StatusEnum.SUBMITTED)


@worker.task()
def submit(circuits: list[Circuit], n_shots: int) -> ExecuteJobRef:
    my_project_ref = qnx.projects.get_or_create(name="Riken-Test")
    qnx.context.set_active_project(my_project_ref)

    my_circuit_refs: list[ExecutionProgram] = []
    for circ in circuits:
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


if __name__ == "__main__":
    worker.app(argv)
