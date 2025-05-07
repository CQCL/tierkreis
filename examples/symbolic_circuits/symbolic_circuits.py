# /// script
# requires-python = ">=3.12"
# dependencies = ["tierkreis", "pytket"]
#
# [tool.uv.sources]
# tierkreis = { path = "../../python" }
# ///
import json
from pathlib import Path
from uuid import UUID

from pytket.circuit import Circuit, fresh_symbol
from tierkreis.controller import run_graph
from tierkreis.controller.data.graph import GraphData, Const, Func, Output, Input
from tierkreis.controller.data.location import Loc
from tierkreis.controller.storage.filestorage import ControllerFileStorage
from tierkreis.controller.executor.uv_executor import UvExecutor

root_loc = Loc()


def build_ansatz() -> Circuit:
    # TODO: This isn't a very good ansatz
    a = fresh_symbol("a")
    b = fresh_symbol("b")
    c = fresh_symbol("c")
    circ = Circuit(4)
    circ.CX(0, 1)
    circ.CX(1, 2)
    circ.CX(2, 3)
    circ.Rz(a, 3)
    circ.CX(2, 3)
    circ.CX(1, 2)
    circ.CX(0, 1)
    circ.Rz(b, 0)
    circ.CX(0, 1)
    circ.CX(1, 2)
    circ.CX(2, 3)
    circ.Rz(c, 3)
    circ.CX(2, 3)
    circ.CX(1, 2)
    circ.CX(0, 1)
    return circ


def symbolic_execution() -> GraphData:
    """A graph that substitutes 3 parameters into a circuit and gets an expectation value."""
    g = GraphData()
    a = g.add(Input("a"))("a")
    b = g.add(Input("b"))("b")
    c = g.add(Input("c"))("c")
    ansatz = g.add(Input("ansatz"))("ansatz")
    n_shots = g.add(Const(100))("value")

    substituted_circuit = g.add(
        Func("pytket_worker.substitute", {"a": a, "b": b, "c": c, "circuit": ansatz})
    )("circuit")

    measurement_circuit = g.add(
        Func("pytket_worker.add_measure_all", {"circuit": substituted_circuit})
    )("circuit")

    # TODO: A better compilation pass
    compiled_circuit = g.add(
        Func("pytket_worker.optimise_phase_gadgets", {"circuit": measurement_circuit})
    )("circuit")

    backend_result = g.add(
        Func(
            "aer_worker.submit_single",
            {"circuit": compiled_circuit, "n_shots": n_shots},
        )
    )("backend_result")

    expectation = g.add(
        Func(
            "pytket_worker.expectation",
            {"backend_result": backend_result},
        )
    )("expectation")

    g.add(Output({"expectation": expectation}))

    return g


def main() -> None:
    """Configure our workflow execution and run it to completion."""
    ansatz = build_ansatz()

    # Assign a fixed uuid for our workflow.
    workflow_id = UUID(int=0)
    storage = ControllerFileStorage(workflow_id, name="symbolic_circuits")

    # Look for workers in the same directory as this file.
    registry_path = Path(__file__).parent
    executor = UvExecutor(registry_path=registry_path, logs_path=storage.logs_path)
    print("Starting workflow at location:", storage.logs_path)
    run_graph(
        storage,
        executor,
        symbolic_execution(),
        {
            "ansatz": json.dumps(ansatz.to_dict()).encode(),
            "a": json.dumps(0.2).encode(),
            "b": json.dumps(0.55).encode(),
            "c": json.dumps(0.75).encode(),
        },
        polling_interval_seconds=0.1,
    )
    output = json.loads(storage.read_output(root_loc, "expectation"))
    print(output)


if __name__ == "__main__":
    main()
