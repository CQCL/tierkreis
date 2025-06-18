# /// script
# requires-python = ">=3.12"
# dependencies = ["pydantic", "tierkreis", "pyscf"]
#
# [tool.uv.sources]
# tierkreis = { path = "../../../tierkreis" }
# ///
import logging
from pathlib import Path
from sys import argv

from chemistry.active_space import get_frozen
from chemistry.molecule import extract_hamiltonian_rhf
from pydantic import BaseModel

from tierkreis import Worker

logger = logging.getLogger(__name__)

worker = Worker("chemistry_worker")


class HamiltonianResult(BaseModel):
    h0: float
    h1: list
    h2: list


@worker.function()
def make_ham(
    geometry: str, basis: str, charge: int, mo_occ: list[int], n_cas: int, n_elecas: int
) -> HamiltonianResult:
    # Construct the frozen orbital lists.
    frozen = get_frozen(mo_occ, n_cas, n_elecas)
    h0, h1, h2 = extract_hamiltonian_rhf(
        geometry,
        basis,
        charge=charge,
        frozen=frozen,
    )
    return HamiltonianResult(h0=h0, h1=h1.tolist(), h2=h2.tolist())


def main() -> None:
    node_definition_path = argv[1]
    worker.run(Path(node_definition_path))


if __name__ == "__main__":
    main()
