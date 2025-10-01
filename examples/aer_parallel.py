from pathlib import Path
from quantinuum_schemas.models.backend_config import AerConfig
from pytket.qasm.qasm import circuit_from_qasm
from tierkreis.graphs.aer.compile_run import aer_compile_run
from uuid import UUID

from tierkreis.consts import PACKAGE_PATH
from tierkreis.controller import run_graph
from tierkreis.storage import FileStorage, read_outputs
from tierkreis.executor import UvExecutor

config = AerConfig()
circuit = circuit_from_qasm(Path(__file__).parent / "data" / "ghz_state_n23.qasm")
circuits = [circuit] * 10


def main():
    g = aer_compile_run()
    storage = FileStorage(UUID(int=107), do_cleanup=True)
    executor = UvExecutor(PACKAGE_PATH / ".." / "tierkreis_workers", storage.logs_path)

    run_graph(
        storage,
        executor,
        g,
        {
            "circuits": circuits,
            "n_shots": [30] * len(circuits),
            "config": config,
            "optimisation_level": None,
            "timeout": None,
        },
        polling_interval_seconds=0.1,
    )
    res = read_outputs(g, storage)
    assert isinstance(res, list)
    print(len(res))


if __name__ == "__main__":
    main()
