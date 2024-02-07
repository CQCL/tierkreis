#!/bin/sh
"exec" "$(dirname $0)/../.venv/bin/python" "$0" "$@"
from __future__ import annotations

import operator
from functools import reduce
from typing import Callable, Dict, List, Type, TypeVar

import pytket.extensions
import pytket.passes
from pytket._tket.circuit import Circuit
from pytket.backends.backend import Backend
from pytket.backends.backendresult import BackendResult
from pytket.qasm.qasm import circuit_from_qasm_str
from sympy.core.symbol import Symbol

from tierkreis.common_types.circuit import (
    BackendResult as ResStruct,
)
from tierkreis.common_types.circuit import (
    Circuit as CircStruct,
)
from tierkreis.common_types.circuit import (
    PytketType,
    PytketWrapper,
)
from tierkreis.core.types import TierkreisType
from tierkreis.worker.namespace import Namespace
from tierkreis.worker.prelude import start_worker_server

root = Namespace()
namespace = root["pytket"]

namespace.add_named_struct("Circuit", CircStruct)


circ_type = TierkreisType.from_python(CircStruct)

T = TypeVar("T", bound=PytketType)
S = TypeVar("S", bound=PytketType)
V = TypeVar("V", bound=PytketWrapper)
W = TypeVar("W", bound=PytketWrapper)


def pytket_wrap(
    wrapper: list[W],
    f: Callable[[list[T]], list[S]],
    target_type: Type[V],
) -> list[V]:
    return [
        target_type.from_pytket_value(c)
        for c in f([w.to_pytket_value() for w in wrapper])
    ]


@namespace.function()
async def load_qasm(qasm: str) -> CircStruct:
    """Load a qasm string in to a circuit."""
    return CircStruct.from_pytket_value(circuit_from_qasm_str(qasm))


@namespace.function()
async def load_circuit_json(json_str: str) -> CircStruct:
    """Load a json string in to a circuit."""
    return CircStruct(json_str=json_str)


@namespace.function()
async def dump_circuit_json(circ: CircStruct) -> str:
    """Dump a circuit in to json string."""
    return circ.json_str


@namespace.function()
async def compile_circuits(
    circuits: list[CircStruct], pass_name: str
) -> list[CircStruct]:
    """Compile a list of circuits.

    :param circuits: Circuits to compile.
    :param pass_name: Name of pass to apply.
    :return: List of compiled circuits.
    """

    def compilation(cs: list[Circuit]) -> list[Circuit]:
        for c in cs:
            getattr(pytket.passes, pass_name)().apply(c)
        return cs

    return pytket_wrap(circuits, compilation, CircStruct)


@namespace.function()
async def execute_circuits(
    circuits: list[CircStruct],
    shots: list[int],
    backend_name: str,
) -> List[ResStruct]:
    from pytket.extensions.qiskit.backends.aer import AerBackend

    available_backends: Dict[str, Callable[..., Backend]] = {
        "AerBackend": AerBackend,
    }

    backend = available_backends[backend_name]()

    def execution(cs: list[Circuit]) -> list[BackendResult]:
        cs = backend.get_compiled_circuits(cs)
        handles = backend.process_circuits(cs, n_shots=shots)
        return backend.get_results(handles)

    return pytket_wrap(circuits, execution, ResStruct)


@namespace.function()
async def execute(
    circuit: CircStruct,
    shots: int,
    backend_name: str,
) -> ResStruct:
    return (await execute_circuits([circuit], [shots], backend_name))[0]


@namespace.function()
async def z_expectation(dist: ResStruct) -> float:
    pure_dist = dist.to_pytket_value().get_distribution()
    return 1 - 2 * sum(
        reduce(operator.xor, map(int, state)) * val for state, val in pure_dist.items()
    )


@namespace.function()
async def substitute_symbols(
    circ: CircStruct, symbs: list[str], params: list[float]
) -> CircStruct:
    def subst(cs: list[Circuit]) -> list[Circuit]:
        for c in cs:
            c.symbol_substitution({Symbol(key): val for key, val in zip(symbs, params)})
        return cs

    return pytket_wrap([circ], subst, CircStruct)[0]


if __name__ == "__main__":
    start_worker_server("pytket_worker", root)
