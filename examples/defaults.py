# ruff: noqa: F821
from pathlib import Path
from typing import NamedTuple
from uuid import UUID
from quantinuum_schemas.models.backend_config import AerConfig
from pytket.qasm.qasm import circuit_from_qasm
from tierkreis import run_graph
from tierkreis.consts import PACKAGE_PATH
from tierkreis.storage import FileStorage, read_outputs
from tierkreis.executor import UvExecutor
from tierkreis.builder import GraphBuilder
from tierkreis.controller.data.models import TKR, OpaqueType
from tierkreis.pytket_worker import compile_tket_circuit_ibm

type Circuit = OpaqueType["pytket._tket.circuit.Circuit"]
type BackendResult = OpaqueType["pytket.backends.backendresult.BackendResult"]

config = AerConfig()
circuit = circuit_from_qasm(Path(__file__).parent / "data" / "ghz_state_n23.qasm")


class InnerInputs(NamedTuple):
    circuit: TKR[Circuit]
    backend_name: TKR[str]
    # optimisation_level: TKR[int]


class OuterInputs(NamedTuple):
    circuit: TKR[Circuit]
    backend_name: TKR[str]
    optimisation_level: TKR[int]


def inner_graph() -> GraphBuilder:
    g = GraphBuilder(InnerInputs, TKR[Circuit])
    compiled_circuit = g.task(
        compile_tket_circuit_ibm(g.inputs.circuit, g.inputs.backend_name)
    )
    g.outputs(compiled_circuit)
    return g


# def outer_graph() -> GraphBuilder:
#     g = GraphBuilder(OuterInputs, TKR[Circuit])
#     compiled_circuit = g.eval(
#         inner_graph(),
#         InnerInputs(
#             g.inputs.circuit,
#             g.inputs.backend_name or g.const("ibm_torino"),
#             g.inputs.optimisation_level,
#         ),
#     )
#     g.outputs(compiled_circuit)
#     return g


if __name__ == "__main__":
    storage = FileStorage(UUID(int=202), do_cleanup=True)
    executor = UvExecutor(PACKAGE_PATH / ".." / "tierkreis_workers", storage.logs_path)
    run_graph(
        storage,
        executor,
        inner_graph(),
        {"circuit": circuit, "backend_name": "ibm_torino"},
        polling_interval_seconds=0.1,
    )
    outputs = read_outputs(inner_graph(), storage)
    assert isinstance(outputs, dict)
    print(len(outputs))
