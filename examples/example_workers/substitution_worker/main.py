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
from pytket._tket.circuit import Circuit
from sympy import Symbol

logger = logging.getLogger(__name__)

worker = Worker("substitution_worker")


class CircuitResult(BaseModel):
    circuit: dict


@worker.function()
def substitute(circuit: dict, a: float, b: float, c: float) -> CircuitResult:
    pytket_circuit = Circuit.from_dict(circuit)
    pytket_circuit.symbol_substitution({Symbol("a"): a, Symbol("b"): b, Symbol("c"): c})
    return CircuitResult(circuit=pytket_circuit.to_dict())


def main() -> None:
    node_definition_path = argv[1]
    worker.run(Path(node_definition_path))


if __name__ == "__main__":
    main()
