from pathlib import Path
from uuid import UUID

from tierkreis.consts import PACKAGE_PATH
from tierkreis.controller import run_graph
from tierkreis.executor import UvExecutor
from tierkreis.storage import FileStorage, read_outputs

from pytket.qasm.qasm import circuit_from_qasm
from pytket.backends.backendresult import BackendResult as BR
from qnexus import AerConfig
from typing import NamedTuple
from tierkreis.builder import GraphBuilder
from tierkreis.builtins.stubs import tkr_sleep
from tierkreis.controller.data.models import TKR, OpaqueType
from example_workers.nexus_worker.stubs import (
    upload_circuit,
    start_execute_job,
    is_running,
    get_results,
)

type Circuit = OpaqueType["pytket._tket.circuit.Circuit"]
type BackendResult = OpaqueType["pytket.backends.backendresult.BackendResult"]
type ExecuteJobRef = OpaqueType["qnexus.models.references.ExecuteJobRef"]
type ExecutionProgram = OpaqueType["qnexus.models.references.ExecuteJobRef"]
aer_config = AerConfig()
circuit = circuit_from_qasm(Path(__file__).parent / "data" / "ghz_state_n23.qasm")
circuits = [circuit]


class UploadCircuitInputs(NamedTuple):
    project_name: TKR[str]
    circuit: TKR[Circuit]


class JobInputs(NamedTuple):
    project_name: TKR[str]
    job_name: TKR[str]
    circuits: TKR[list[Circuit]]
    n_shots: TKR[list[int]]
    backend_config: TKR[OpaqueType["qnexus.BackendConfig"]]


class LoopOutputs(NamedTuple):
    results: TKR[list[BackendResult]]
    should_continue: TKR[bool]


def upload_circuit_graph():
    g = GraphBuilder(UploadCircuitInputs, TKR[ExecutionProgram])
    programme = g.task(upload_circuit(g.inputs.project_name, g.inputs.circuit))
    g.outputs(programme)  # type: ignore
    return g


def polling_loop_body(polling_interval: float):
    g = GraphBuilder(TKR[ExecuteJobRef], LoopOutputs)
    pred = g.task(is_running(g.inputs))

    wait = g.ifelse(pred, g.task(tkr_sleep(g.const(polling_interval))), g.const(False))
    results = g.ifelse(pred, g.const([]), g.task(get_results(g.inputs)))

    g.outputs(LoopOutputs(results=results, should_continue=wait))
    return g


def nexus_submit_and_poll(polling_interval: float = 30.0):
    g = GraphBuilder(JobInputs, TKR[list[BackendResult]])
    upload_inputs = g.map(
        lambda x: UploadCircuitInputs(g.inputs.project_name, x), g.inputs.circuits
    )
    programmes = g.map(upload_circuit_graph(), upload_inputs)

    ref = g.task(
        start_execute_job(
            g.inputs.project_name,
            g.inputs.job_name,
            programmes,  # type: ignore
            g.inputs.n_shots,
            g.inputs.backend_config,  # type: ignore
        )
    )

    res = g.loop(polling_loop_body(polling_interval), ref)
    g.outputs(res.results)
    return g


def main():
    g = nexus_submit_and_poll()
    storage = FileStorage(UUID(int=107), do_cleanup=True)
    executor = UvExecutor(PACKAGE_PATH / ".." / "tierkreis_workers", storage.logs_path)

    run_graph(
        storage,
        executor,
        g,
        {
            "project_name": "2025-tkr-test",
            "job_name": "job-1",
            "circuits": circuits,
            "n_shots": [30] * len(circuits),
            "backend_config": aer_config,
        },
        polling_interval_seconds=0.1,
    )
    res = read_outputs(g, storage)
    print(res)


if __name__ == "__main__":
    main()
