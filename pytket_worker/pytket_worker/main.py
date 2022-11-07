#!/bin/sh
"exec" "$(dirname $0)/../.venv/bin/python" "$0" "$@"
from __future__ import annotations

import json
import operator
from dataclasses import dataclass
from functools import reduce
from typing import Callable, Dict, List

import pytket.extensions
import pytket.passes  # type: ignore
from pytket.backends import Backend
from pytket.circuit import Circuit  # type: ignore
from pytket.qasm.qasm import circuit_from_qasm_str
from sympy.core.symbol import Symbol  # type: ignore

from tierkreis.common_types import SampledDistribution, backres_to_sampleddist
from tierkreis.common_types.circuit import BitRegister, CircBox
from tierkreis.common_types.circuit import Circuit as CircStruct
from tierkreis.common_types.circuit import (
    Command,
    Conditional,
    GenericClassical,
    Operation,
    Permutation,
    UnitID,
)
from tierkreis.core.tierkreis_struct import TierkreisStruct
from tierkreis.core.types import TierkreisType
from tierkreis.worker.namespace import Namespace
from tierkreis.worker.prelude import start_worker_server

root = Namespace()
namespace = root["pytket"]

_ = [
    namespace.add_named_struct(thing.__name__, thing)
    for thing in (
        Command,
        UnitID,
        Conditional,
        BitRegister,
        Operation,
        CircStruct,
        Permutation,
        CircBox,
        GenericClassical,
    )
]

SampledDistribution = namespace.add_named_struct(
    "SampledDistribution", SampledDistribution
)


@dataclass
class CircArg(TierkreisStruct):
    value: CircStruct


circ_type = TierkreisType.from_python(CircStruct)


def _load_circstruct(struc: CircStruct) -> Circuit:
    return struc.to_pytket_circuit()


def _dump_circstruct(circ: Circuit) -> CircStruct:
    return CircStruct.from_pytket_circuit(circ)


@namespace.function()
async def load_qasm(qasm: str) -> CircArg:
    """Load a qasm string in to a circuit."""
    return CircArg(_dump_circstruct(circuit_from_qasm_str(qasm)))


@namespace.function()
async def load_circuit_json(json_str: str) -> CircArg:
    """Load a json string in to a circuit."""
    return CircArg(_dump_circstruct(Circuit.from_dict(json.loads(json_str))))


@namespace.function()
async def dump_circuit_json(circ: CircStruct) -> str:
    """Dump a circuit in to json string."""
    return json.dumps(circ.to_serializable())


@namespace.function()
async def compile_circuits(
    circuits: list[CircStruct], pass_name: str
) -> list[CircStruct]:
    """Compile a list of circuits.

    :param circuits: Circuits to compile.
    :param pass_name: Name of pass to apply.
    :return: List of compiled circuits.
    """
    pycircs = list(map(_load_circstruct, circuits))
    for circuit in pycircs:
        getattr(pytket.passes, pass_name)().apply(circuit)
    return list(map(_dump_circstruct, pycircs))


@namespace.function()
async def execute_circuits(
    circuits: list[CircStruct],
    shots: list[int],
    backend_name: str,
) -> List[SampledDistribution]:

    from pytket.extensions.qiskit import AerBackend  # type: ignore

    available_backends: Dict[str, Callable[..., Backend]] = {
        "AerBackend": AerBackend,
    }

    backend = available_backends[backend_name]()
    circuits = backend.get_compiled_circuits(list(map(_load_circstruct, circuits)))
    handles = backend.process_circuits(circuits, n_shots=shots)
    return [backres_to_sampleddist(res) for res in backend.get_results(handles)]


@namespace.function()
async def execute(
    circuit: CircStruct,
    shots: int,
    backend_name: str,
) -> SampledDistribution:

    return (await execute_circuits([circuit], [shots], backend_name))[0]


@namespace.function()
async def z_expectation(dist: SampledDistribution) -> float:
    pure_dist = dist.distribution
    return 1 - 2 * sum(
        reduce(operator.xor, map(int, state)) * val for state, val in pure_dist.items()
    )


@namespace.function()
async def substitute_symbols(
    circ: CircStruct, symbs: list[str], params: list[float]
) -> CircArg:
    # TODO use Dict[str, float] once there are make/unmake map builtins0
    tkcirc = _load_circstruct(circ)
    tkcirc.symbol_substitution({Symbol(key): val for key, val in zip(symbs, params)})
    return CircArg(_dump_circstruct(tkcirc))


if __name__ == "__main__":
    start_worker_server("pytket_worker", root)
