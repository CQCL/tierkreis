# /// script
# requires-python = ">=3.12"
# dependencies = ["tierkreis", "pytket"]
#
# [tool.uv.sources]
# tierkreis = { path = "../tierkreis", editable = true }
# ///
import json
from pathlib import Path
from uuid import UUID

from tierkreis.controller import run_graph
from tierkreis.controller.data.graph import GraphData
from tierkreis.controller.data.location import Loc
from tierkreis.controller.executor.multiple import MultipleExecutor
from tierkreis.controller.executor.uv_executor import UvExecutor
from tierkreis.controller.storage.filestorage import ControllerFileStorage

root_loc = Loc()


def _compile_and_run() -> GraphData:
    g = GraphData()
    circuit = g.input("circuit")
    n_shots = g.const(500)

    out = g.func("pytket_worker.compile_circuit_quantinuum", {"circuit": circuit})

    backend_result = g.func(
        "aer_worker.submit_single",
        {"circuit": out("circuit"), "n_shots": n_shots},
    )("backend_result")

    g.output({"backend_result": backend_result})
    return g


def qsci_graph() -> GraphData:
    g = GraphData()
    geometry = g.input("geometry")
    basis = g.input("basis")
    charge = g.input("charge")
    mo_occ = g.input("mo_occ")
    # init
    n_cas_init = g.input("n_cas_init")
    n_elecas_init = g.input("n_elecas_init")
    # hsim
    n_cas_hsim = g.input("n_cas_hsim")
    n_elecas_hsim = g.input("n_elecas_hsim")

    # Functions 'make_h_init'+'state_pre' and 'make_h_hsim' run in parallel
    h_init = g.func(
        "chemistry_worker.make_ham",
        {
            "geometry": geometry,
            "basis": basis,
            "charge": charge,
            "mo_occ": mo_occ,
            "n_cas": n_cas_init,
            "n_elecas": n_elecas_init,
        },
    )
    h0_init = h_init("h0")
    h1_init = h_init("h1")
    h2_init = h_init("h2")

    h_hsim = g.func(
        "chemistry_worker.make_ham",
        {
            "geometry": geometry,
            "basis": basis,
            "charge": charge,
            "mo_occ": mo_occ,
            "n_cas": n_cas_hsim,
            "n_elecas": n_elecas_hsim,
        },
    )
    h0_hsim = h_hsim("h0")
    h1_hsim = h_hsim("h1")
    h2_hsim = h_hsim("h2")

    reference_state = g.input("reference_state")
    max_iteration_prep = g.input("max_iteration_prep")
    atol = g.input("atol")

    state_prep = g.func(
        "qsci_worker.state_prep",
        {
            "h0_init": h0_init,
            "h1_init": h1_init,
            "h2_init": h2_init,
            "reference_state": reference_state,
            "max_iteration_prep": max_iteration_prep,
            "atol": atol,
            "mo_occ": mo_occ,
            "n_cas_init": n_cas_init,
            "n_elecas_init": n_elecas_init,
            "n_cas_hsim": n_cas_hsim,
            "n_elecas_hsim": n_elecas_hsim,
        },
    )
    adapt_circuit = state_prep("adapt_circuit")

    t_step_list = g.input("t_step_list")
    max_cx_gates_hsim = g.input("max_cx_gates_hsim")

    circuits = g.func(
        "qsci_worker.circuits_from_hamiltonians",
        {
            "h0_init": h0_init,
            "h1_init": h1_init,
            "h2_init": h2_init,
            "h0_hsim": h0_hsim,
            "h1_hsim": h1_hsim,
            "h2_hsim": h2_hsim,
            "adapt_circuit": adapt_circuit,
            "t_step_list": t_step_list,
            "n_elecas_init": n_elecas_init,
            "n_elecas_hsim": n_elecas_hsim,
            "n_cas_hsim": n_cas_hsim,
            "mo_occ": mo_occ,
            "max_cx_gates": max_cx_gates_hsim,
        },
    )("circuits")

    unfolded_circuits = g.func("builtins.unfold_values", {"value": circuits})

    compile_and_run_const = g.const(_compile_and_run())
    m = g.map(
        compile_and_run_const,
        unfolded_circuits("*")[0],
        "circuit",
        "backend_result",
        {},
    )
    backend_results = g.func("builtins.fold_values", {"values_glob": m("*")})("value")

    energy = g.func(
        "qsci_worker.energy_from_results",
        {
            "h0_hsim": h0_hsim,
            "h1_hsim": h1_hsim,
            "h2_hsim": h2_hsim,
            "backend_results": backend_results,
            "mo_occ": mo_occ,
            "n_elecas_init": n_elecas_init,
            "n_elecas_hsim": n_elecas_hsim,
            "n_cas_init": n_cas_init,
            "n_cas_hsim": n_cas_hsim,
        },
    )("energy")

    g.output({"energy": energy})

    return g


def main() -> None:
    """Configure our workflow execution and run it to completion."""
    # Assign a fixed uuid for our workflow.
    workflow_id = UUID(int=104)
    storage = ControllerFileStorage(workflow_id, name="qsci", do_cleanup=True)

    # Look for workers in the same directory as this file.
    registry_path = Path(__file__).parent
    # Look for workers in the `example_workers` directory.
    registry_path = Path(__file__).parent / "example_workers"
    custom_executor = UvExecutor(
        registry_path=registry_path, logs_path=storage.logs_path
    )
    common_registry_path = Path(__file__).parent.parent / "tierkreis_workers"
    common_executor = UvExecutor(
        registry_path=common_registry_path, logs_path=storage.logs_path
    )
    multi_executor = MultipleExecutor(
        common_executor,
        executors={"custom": custom_executor},
        assignments={"chemistry_worker": "custom", "qsci_worker": "custom"},
    )
    print("Starting workflow at location:", storage.logs_path)

    run_graph(
        storage,
        multi_executor,
        qsci_graph(),
        {
            k: json.dumps(v).encode()
            for k, v in (
                {
                    "basis": "sto-3g",
                    "charge": 0,
                    "geometry": [
                        ["H", [0, 0, 0]],
                        ["H", [0, 0, 1.0]],
                        ["H", [0, 0, 2.0]],
                        ["H", [0, 0, 3.0]],
                    ],
                    "max_cx_gates_hsim": 2000,
                    "mo_occ": [2, 2, 0, 0],
                    "reference_state": [1, 1, 0, 0],
                    "n_cas_init": 2,
                    "n_elecas_init": 2,
                    "n_cas_hsim": 4,
                    "n_elecas_hsim": 4,
                    "t_step_list": [0.5, 1.0, 1.5],
                    "max_iteration_prep": 5,
                    "atol": 0.03,
                }
            ).items()
        },
        polling_interval_seconds=0.01,
    )
    output = json.loads(storage.read_output(root_loc, "energy"))
    print(output)


if __name__ == "__main__":
    main()
