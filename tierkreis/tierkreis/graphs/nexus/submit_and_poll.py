from typing import NamedTuple
from tierkreis.builder import GraphBuilder
from tierkreis.controller.data.models import TKR, OpaqueType
from tierkreis_workers.nexus_worker.stubs import (
    upload_circuit,
    start_execute_job,
    status,
    get_results,
)
from tierkreis.builtins.stubs import enumerate_list, unzip, concat

type Circuit = OpaqueType["pytket._tket.circuit.Circuit"]
type BackendResult = OpaqueType["pytket.backends.backendresult.BackendResult"]
type ExecuteJobRef = OpaqueType["qnexus.models.references.ExecuteJobRef"]
type ExecutionProgram = OpaqueType["qnexus.models.references.ExecutionProgram"]


class NamedCircuit(NamedTuple):
    name: str
    circuit: Circuit


class UploadCircuitInputs(NamedTuple):
    project_name: TKR[str]
    circuit_name: TKR[str]
    circuit: TKR[Circuit]


def upload_circuit_graph():
    g = GraphBuilder(UploadCircuitInputs, TKR[list[ExecutionProgram]])
    return g.task(
        upload_circuit(g.inputs.project_name, g.inputs.circuit_name, g.inputs.circuit)
    )


class UploadCircuitsInputs(NamedTuple):
    project_name: TKR[str]
    circuits: TKR[NamedCircuit]


class NameCircuitInputs(NamedTuple):
    idx: TKR[str]
    circuit_name_prefix: TKR[str]
    circuit: TKR[Circuit]


def upload_circuits():
    g = GraphBuilder(UploadCircuitsInputs, TKR[list[ExecutionProgram]])
    unzipped_enumeration = g.task(unzip(enumeration))

    indices = g.map(lambda x: x, unzipped_enumeration.a)

    upload_inputs = g.map(
        lambda x: UploadCircuitInputs(g.inputs.project_name, "a", x), enumeration
    )


def nexus_submit_and_poll():
    g = GraphBuilder(TKR[list[Circuit]], TKR[list[BackendResult]])
