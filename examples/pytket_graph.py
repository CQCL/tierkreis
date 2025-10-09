# /// script
# requires-python = ">=3.12"
# dependencies = ["tierkreis", "pytket"]
#
# [tool.uv.sources]
# tierkreis = { path = "../tierkreis", editable = true }
# ///
from uuid import UUID
from pathlib import Path
from typing import NamedTuple

from pytket._tket.circuit import Circuit
from pytket.backends.backendresult import BackendResult

from tierkreis.builder import GraphBuilder

from tierkreis.controller.data.models import TKR, OpaqueType
from tierkreis.controller import run_graph
from tierkreis.storage import read_outputs, InMemoryStorage
from tierkreis.controller.executor.in_memory_executor import InMemoryExecutor
from tierkreis.pytket_worker import compile_tket_circuit_ibm
from tierkreis.aer_worker import submit_single


def ghz() -> Circuit:
    circ1 = Circuit(2)
    circ1.H(0)
    circ1.CX(0, 1)
    circ1.measure_all()
    return circ1


class IBMInput(NamedTuple):
    circuit: TKR[OpaqueType["pytket._tket.circuit.Circuit"]]  # noqa: F821
    n_shots: TKR[int]
    backend: TKR[str]


def compile_run_single():
    g = GraphBuilder(
        IBMInput, TKR[OpaqueType["pytket.backends.backendresult.BackendResult"]]
    )

    compiled_circuit = g.task(
        compile_tket_circuit_ibm(
            circuit=g.inputs.circuit,
            backend_name=g.inputs.backend,
            optimization_level=g.const(2),
        )
    )
    res = g.task(submit_single(compiled_circuit, g.inputs.n_shots))
    g.outputs(res)
    return g


def main():
    g = compile_run_single()
    storage = InMemoryStorage(UUID(int=109))
    executor = InMemoryExecutor(
        Path(__file__).parent.parent / "tierkreis_workers", storage
    )
    n_shots = 30
    run_graph(
        storage,
        executor,
        g,
        {
            "circuit": ghz(),
            "n_shots": n_shots,
        },
        polling_interval_seconds=0.1,
    )
    res = read_outputs(g, storage)
    assert isinstance(res, BackendResult)
    assert len(res.get_shots()) == n_shots
    print(res)


if __name__ == "__main__":
    main()
