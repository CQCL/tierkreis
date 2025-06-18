# /// script
# requires-python = ">=3.12"
# dependencies = ["pydantic", "pytket", "tierkreis"]
#
# [tool.uv.sources]
# tierkreis = { path = "../../../tierkreis" }
# ///
import logging
from pathlib import Path
from sys import argv
from typing import Counter, cast

import numpy as np
from pydantic import BaseModel
from pytket._tket.circuit import Circuit
from pytket.backends.backendresult import BackendResult
from pytket.circuit import Qubit
from pytket.pauli import QubitPauliString
from pytket.utils.operators import CoeffTypeAccepted, QubitPauliOperator
from qsci.active_space import get_n_active, get_n_core
from qsci.jordan_wigner import qubit_mapping_jordan_wigner
from qsci.postprocess import get_ci_matrix, postprocess_configs
from qsci.state_prep import perform_state_preparation
from qsci.utils import get_config_from_cas_init, make_time_evolution_circuits, rhf2ghf

from tierkreis import Worker

logger = logging.getLogger(__name__)

worker = Worker("qsci_worker")


class AdaptCircuitResult(BaseModel):
    adapt_circuit: dict


@worker.function()
def state_prep(
    h0_init: float,
    h1_init: list,
    h2_init: list,
    reference_state: list[int],
    max_iteration_prep: int,
    atol: float,
    mo_occ: list[int],
    n_elecas_init: int,
    n_elecas_hsim: int,
    n_cas_init: int,
    n_cas_hsim: int,
) -> AdaptCircuitResult:
    ham_init_operator = QubitPauliOperator(
        cast(
            dict[QubitPauliString, CoeffTypeAccepted],
            qubit_mapping_jordan_wigner(
                *rhf2ghf(
                    h0_init,
                    np.array(h1_init),
                    np.array(h2_init),
                )
            ),
        )
    )
    # time-evolve CASCI ground state.
    n_core_init = get_n_core(mo_occ, n_elecas_init)
    n_core_hsim = get_n_core(mo_occ, n_elecas_hsim)
    n_core = n_core_init - n_core_hsim
    logging.info(
        f"mo_occ={mo_occ} n_cas_hsim={n_cas_hsim} n_elecas_hsim={n_elecas_hsim}"
    )
    n_active_hsim = get_n_active(mo_occ, n_cas_hsim, n_elecas_hsim)
    prepared_circ = Circuit(n_active_hsim * 2)
    for i in range(n_core * 2):
        prepared_circ.X(i)
    adapt_circ = perform_state_preparation(
        reference_state=reference_state,
        ham_init=ham_init_operator,
        n_cas_init=n_cas_init,
        max_iteration=max_iteration_prep,
        atol=atol,
    )

    return AdaptCircuitResult(adapt_circuit=adapt_circ.to_dict())


class TimeEvolutionCircuitsResult(BaseModel):
    circuits: list[dict]


@worker.function()
def circuits_from_hamiltonians(
    h0_init: float,
    h1_init: list,
    h2_init: list,
    h0_hsim: float,
    h1_hsim: list,
    h2_hsim: list,
    adapt_circuit: dict,
    t_step_list: list[float],
    n_elecas_init: int,
    n_elecas_hsim: int,
    n_cas_hsim: int,
    mo_occ: list[int],
    max_cx_gates: int,
) -> TimeEvolutionCircuitsResult:
    pytket_adapt_circuit = Circuit.from_dict(adapt_circuit)
    ham_init_operator = QubitPauliOperator(
        cast(
            dict[QubitPauliString, CoeffTypeAccepted],
            qubit_mapping_jordan_wigner(
                *rhf2ghf(
                    h0_init,
                    np.array(h1_init),
                    np.array(h2_init),
                )
            ),
        )
    )
    ham_hsim_operator = QubitPauliOperator(
        cast(
            dict[QubitPauliString, CoeffTypeAccepted],
            qubit_mapping_jordan_wigner(
                *rhf2ghf(
                    h0_hsim,
                    np.array(h1_hsim),
                    np.array(h2_hsim),
                )
            ),
        )
    )
    # Load the input data.
    n_core_init = get_n_core(mo_occ, n_elecas_init)
    n_core_hsim = get_n_core(mo_occ, n_elecas_hsim)
    n_core = n_core_init - n_core_hsim
    n_active_hsim = get_n_active(mo_occ, n_cas_hsim, n_elecas_hsim)
    prepared_circ = Circuit(n_active_hsim * 2)
    for i in range(n_core * 2):
        prepared_circ.X(i)
    prepared_circ.add_circuit(
        pytket_adapt_circuit,
        [2 * n_core + i for i in range(pytket_adapt_circuit.n_qubits)],
    )
    ham_init_shifted = QubitPauliOperator(
        {
            QubitPauliString(
                {
                    Qubit(qubit.index[0] + 2 * n_core): pauli
                    for qubit, pauli in qps.map.items()
                }
            ): coeff
            for qps, coeff in ham_init_operator._dict.items()
        }
    )
    circuits = make_time_evolution_circuits(
        t_step_list,
        prepared_circ,
        h_hsim=ham_hsim_operator,
        h_init=ham_init_shifted,
        max_cx_gates=max_cx_gates,
    )
    return TimeEvolutionCircuitsResult(circuits=[x.to_dict() for x in circuits])


class EnergyResult(BaseModel):
    energy: float


@worker.function()
def energy_from_results(
    h0_hsim: float,
    h1_hsim: list,
    h2_hsim: list,
    backend_results: list[dict],
    mo_occ: list[int],
    n_elecas_init: int,
    n_elecas_hsim: int,
    n_cas_init: int,
    n_cas_hsim: int,
) -> EnergyResult:
    pytket_backend_results = [BackendResult.from_dict(x) for x in backend_results]
    counts = Counter()
    for r in pytket_backend_results:
        for k, v in r.get_counts().items():
            counts[k] += v
    phis = list(counts.keys())
    phis_init_orig = get_config_from_cas_init(
        mo_occ, n_cas_init, n_elecas_init, n_cas_hsim, n_elecas_hsim
    )
    for p in phis_init_orig:
        if p not in phis:
            phis.append(p)
    # phis = get_config(backend_results)
    logger.info(f"CONFIG (before): {len(phis)}")
    phis = postprocess_configs(phis_init_orig[0], phis)
    logger.info(f"CONFIG (after):  {len(phis)}")

    hsd = get_ci_matrix(
        phis,
        h1=np.array(h1_hsim),
        h2=np.array(h2_hsim),
        enuc=h0_hsim,
    )
    energy = np.linalg.eigh(hsd.todense())[0][0]
    logger.info(f"ENERGY: {energy}")

    return EnergyResult(energy=energy)


def main() -> None:
    node_definition_path = argv[1]
    worker.run(Path(node_definition_path))


if __name__ == "__main__":
    main()
