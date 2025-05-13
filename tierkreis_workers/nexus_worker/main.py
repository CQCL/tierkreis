import json
import logging
import os
from datetime import datetime
from pathlib import Path
from sys import argv
from typing import Optional

import qnexus as qnx
from dotenv import load_dotenv
from pydantic import BaseModel
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


class NodeDefinition(BaseModel):
    function_name: str
    inputs: dict[str, Path]
    outputs: dict[str, Path]
    done_path: Path
    logs_path: Optional[Path] = None


def setup_project():
    refresh_token = os.environ.get("NEXUS_REFRESH_TOKEN")
    assert refresh_token is not None
    write_token("refresh_token", refresh_token)


def check_status(job_ref: ExecuteJobRef, delay: int) -> StatusEnum:
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


def run(node_definition: NodeDefinition):
    logging.basicConfig(
        format="%(asctime)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
        filename=node_definition.logs_path,
        filemode="a",
        level=logging.INFO,
    )
    logger.info(node_definition.model_dump())

    name = node_definition.function_name
    if name == "submit":
        with open(node_definition.inputs["circuits"], "rb") as fh:
            circuit_jsons = json.loads(fh.read())
            assert isinstance(circuit_jsons, list)
            circuits = [Circuit.from_dict(x) for x in circuit_jsons]  # type:ignore

        with open(node_definition.inputs["n_shots"], "rb") as fh:
            n_shots = json.loads(fh.read())
            assert isinstance(n_shots, int)

        execute_ref = execute_circuits(
            circuits,
            n_shots=n_shots,
            backend_name="H1-1LE",
            project_name="Riken-Test",
        )

        with open(node_definition.outputs["execute_ref"], "w+") as fh:
            fh.write(execute_ref.model_dump_json())

    elif name == "check_status":
        with open(node_definition.inputs["execute_ref"], "rb") as fh:
            execute_ref = ExecuteJobRef(**json.loads(fh.read()))

        status_enum = check_status(execute_ref, 30)

        with open(node_definition.outputs["status_enum"], "w+") as fh:
            fh.write(json.dumps(status_enum.name))

    elif name == "get_results":
        with open(node_definition.inputs["execute_ref"], "rb") as fh:
            execute_ref = ExecuteJobRef(**json.loads(fh.read()))

        results = get_backend_results(execute_ref)

        with open(node_definition.outputs["backend_results"], "w+") as fh:
            fh.write(json.dumps([x.to_dict() for x in results]))

    else:
        raise ValueError(f"nexus-worker: unknown function: {name}")

    node_definition.done_path.touch()


def main():
    node_definition_path = argv[1]
    with open(node_definition_path, "r") as fh:
        node_definition = NodeDefinition(**json.loads(fh.read()))
    run(node_definition)


if __name__ == "__main__":
    main()
