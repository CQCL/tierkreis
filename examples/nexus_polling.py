from pathlib import Path
from uuid import UUID

from tierkreis.consts import PACKAGE_PATH
from tierkreis.controller import run_graph
from tierkreis.executor import UvExecutor
from tierkreis.graphs.nexus.submit_and_poll import nexus_submit_and_poll
from tierkreis.storage import FileStorage

from pytket.qasm.qasm import circuit_from_qasm
from qnexus import AerConfig

aer_config = AerConfig()
circuit = circuit_from_qasm(Path(__file__).parent / "data" / "ghz_state_n23.qasm")
# circuit.name = "tkr-test"

circuits = [circuit]


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
    )


if __name__ == "__main__":
    main()
