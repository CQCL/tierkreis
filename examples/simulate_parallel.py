from pathlib import Path
import time
from pytket.qasm.qasm import circuit_from_qasm
from tierkreis.graphs.simulate.compile_simulate import compile_simulate
from uuid import UUID

from tierkreis.consts import PACKAGE_PATH
from tierkreis.controller import run_graph
from tierkreis.storage import FileStorage, read_outputs
from tierkreis.executor import UvExecutor

simulator_name = "aer"
circuit = circuit_from_qasm(Path(__file__).parent / "data" / "ghz_state_n23.qasm")
circuits = [circuit] * 3


def main():
    g = compile_simulate()
    storage = FileStorage(UUID(int=107), do_cleanup=True)
    executor = UvExecutor(PACKAGE_PATH / ".." / "tierkreis_workers", storage.logs_path)
    inputs = {
        "circuits": circuits,
        "n_shots": [3] * len(circuits),
        "simulator_name": simulator_name,
        "compilation_optimisation_level": 2,
    }

    print("Simulating using aer...")
    start = time.time()
    run_graph(storage, executor, g, inputs, polling_interval_seconds=0.1)
    print(f"time taken: {time.time()-start}")
    res = read_outputs(g, storage)
    assert isinstance(res, list)
    print(len(res))

    inputs["simulator_name"] = "qulacs"

    print("Simulating using qulacs...")
    storage.clean_graph_files()
    start = time.time()
    run_graph(storage, executor, g, inputs, polling_interval_seconds=0.1)
    print(f"time taken: {time.time()-start}")
    res = read_outputs(g, storage)
    assert isinstance(res, list)
    print(len(res))


if __name__ == "__main__":
    main()
