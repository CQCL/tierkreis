# /// script
# requires-python = ">=3.12"
# dependencies = ["pydantic", "pytket", "tierkreis"]
#
# [tool.uv.sources]
# tierkreis = { path = "../../../tierkreis" }
# ///
import logging
from sys import argv
from pathlib import Path


from pydantic import BaseModel
from tierkreis import Worker
from pytket.backends.backendresult import BackendResult
from pytket._tket.circuit import Circuit
from pytket.transform import Transform
from pytket.utils.expectations import expectation_from_counts
from sympy import Symbol

logger = logging.getLogger(__name__)

worker = Worker("pytket-worker")


class CircuitResult(BaseModel):
    circuit: dict


@worker.function()
def substitute(circuit: dict, a: float, b: float, c: float) -> CircuitResult:
    pytket_circuit = Circuit.from_dict(circuit)
    pytket_circuit.symbol_substitution({Symbol("a"): a, Symbol("b"): b, Symbol("c"): c})
    return CircuitResult(circuit=pytket_circuit.to_dict())


@worker.function()
def add_measure_all(circuit: dict) -> CircuitResult:
    pytket_circuit = Circuit.from_dict(circuit)
    pytket_circuit.measure_all()
    return CircuitResult(circuit=pytket_circuit.to_dict())


@worker.function()
def optimise_phase_gadgets(circuit: dict) -> CircuitResult:
    pytket_circuit = Circuit.from_dict(circuit)
    Transform.OptimisePhaseGadgets().apply(pytket_circuit)
    return CircuitResult(circuit=pytket_circuit.to_dict())


class ExpectationResult(BaseModel):
    expectation: float


@worker.function()
def expectation(backend_result: dict) -> ExpectationResult:
    result = BackendResult.from_dict(backend_result)
    expectation = expectation_from_counts(result.get_counts())
    return ExpectationResult(expectation=expectation)


def main() -> None:
    node_definition_path = argv[1]
    worker.run(Path(node_definition_path))


if __name__ == "__main__":
    main()
