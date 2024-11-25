#!/bin/sh
"exec" "$(dirname $0)/../.venv/bin/python" "$0" "$@"
from __future__ import annotations

import json
import operator
from functools import reduce
from typing import Callable, Dict, List

import pytket.extensions
import pytket.passes
from pytket._tket.circuit import Circuit
from pytket.backends.backend import Backend
from pytket.backends.backendresult import BackendResult
from pytket.qasm.qasm import circuit_from_qasm_str
from sympy.core.symbol import Symbol

from tierkreis.common_types.circuit import register_pytket_types
from tierkreis.worker.namespace import Namespace
from tierkreis.worker.prelude import start_worker_server

root = Namespace()
namespace = root["pytket"]

register_pytket_types()
namespace.add_named_struct("Circuit", Circuit)


@namespace.function()
async def load_qasm(qasm: str) -> Circuit:
    """Load a qasm string in to a circuit."""
    return circuit_from_qasm_str(qasm)


@namespace.function()
async def load_circuit_json(json_str: str) -> Circuit:
    """Load a json string in to a circuit."""
    return Circuit.from_dict(json.loads(json_str))


@namespace.function()
async def dump_circuit_json(circ: Circuit) -> str:
    """Dump a circuit in to json string."""
    return json.dumps(circ.to_dict())


@namespace.function()
async def compile_circuits(circuits: list[Circuit], pass_name: str) -> list[Circuit]:
    """Compile a list of circuits.

    :param circuits: Circuits to compile.
    :param pass_name: Name of pass to apply.
    :return: List of compiled circuits.
    """

    for c in circuits:
        getattr(pytket.passes, pass_name)().apply(c)
    return circuits


@namespace.function()
async def execute_circuits(
    circuits: list[Circuit],
    shots: list[int],
    backend_name: str,
) -> List[BackendResult]:
    from pytket.extensions.qiskit.backends.aer import AerBackend

    available_backends: Dict[str, Callable[..., Backend]] = {
        "AerBackend": AerBackend,
    }

    backend = available_backends[backend_name]()

    circuits = backend.get_compiled_circuits(circuits)
    handles = backend.process_circuits(circuits, n_shots=shots)
    return backend.get_results(handles)


@namespace.function()
async def execute(
    circuit: Circuit,
    shots: int,
    backend_name: str,
) -> BackendResult:
    return (await execute_circuits([circuit], [shots], backend_name))[0]


@namespace.function()
async def z_expectation(dist: BackendResult) -> float:
    pure_dist = dist.get_distribution()
    return 1 - 2 * sum(
        reduce(operator.xor, map(int, state)) * val for state, val in pure_dist.items()
    )


@namespace.function()
async def substitute_symbols(
    circ: Circuit, symbs: list[str], params: list[float]
) -> Circuit:
    circ.symbol_substitution({Symbol(key): val for key, val in zip(symbs, params)})
    return circ


if __name__ == "__main__":
    start_worker_server("pytket_worker", root)
