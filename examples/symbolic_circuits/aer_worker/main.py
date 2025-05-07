# /// script
# requires-python = ">=3.12"
# dependencies = ["pydantic", "pytket", "pytket-qiskit"]
# ///
import json
import logging
from sys import argv
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

from pytket._tket.circuit import Circuit
from pytket.extensions.qiskit.backends.aer import AerBackend

logger = logging.getLogger(__name__)


class NodeDefinition(BaseModel):
    function_name: str
    inputs: dict[str, Path]
    outputs: dict[str, Path]
    done_path: Path
    logs_path: Optional[Path] = None


def run(node_definition: NodeDefinition):
    logging.basicConfig(
        format="%(asctime)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
        filename=node_definition.logs_path,
        filemode="a",
        level=logging.INFO,
    )
    logger.info(node_definition.model_dump())

    name = node_definition.function_name

    if name == "submit":
        logger.info("simulate on aer")
        with open(node_definition.inputs["circuits"], "rb") as fh:
            circuit_jsons = json.loads(fh.read())
            assert isinstance(circuit_jsons, list)
            compiled_circuits = [
                Circuit.from_dict(x)
                for x in circuit_jsons  # type:ignore
            ]
        with open(node_definition.inputs["n_shots"], "rb") as fh:
            n_shots = json.loads(fh.read())
            assert isinstance(n_shots, int)

        backend = AerBackend()
        results = backend.run_circuits(compiled_circuits, n_shots=n_shots)

        with open(node_definition.outputs["backend_results"], "w+") as fh:
            fh.write(json.dumps([x.to_dict() for x in results]))

    elif name == "submit_single":
        logger.info("simulate single on aer")
        with open(node_definition.inputs["circuit"], "rb") as fh:
            circuit_json = json.loads(fh.read())
            assert isinstance(circuit_json, dict)
            compiled_circuit = Circuit.from_dict(circuit_json)
        with open(node_definition.inputs["n_shots"], "rb") as fh:
            n_shots = json.loads(fh.read())
            assert isinstance(n_shots, int)

        backend = AerBackend()
        result = backend.run_circuit(compiled_circuit, n_shots=n_shots)

        with open(node_definition.outputs["backend_result"], "w+") as fh:
            fh.write(json.dumps(result.to_dict()))
    else:
        raise ValueError(f"aer-worker: unknown function: {name}")

    node_definition.done_path.touch()


def main():
    logger.info("main")
    node_definition_path = argv[1]
    with open(node_definition_path, "r") as fh:
        node_definition = NodeDefinition(**json.loads(fh.read()))
    run(node_definition)


if __name__ == "__main__":
    main()
