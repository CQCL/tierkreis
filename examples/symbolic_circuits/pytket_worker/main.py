# /// script
# requires-python = ">=3.12"
# dependencies = ["pydantic", "pytket"]
# ///
import json
import logging
from sys import argv
from pathlib import Path
from typing import Optional


from pydantic import BaseModel
from pytket.backends.backendresult import BackendResult
from pytket.circuit import Circuit
from pytket.transform import Transform
from pytket.utils import expectation_from_counts
from sympy import Symbol

logger = logging.getLogger(__name__)


class NodeDefinition(BaseModel):
    function_name: str
    inputs: dict[str, Path]
    outputs: dict[str, Path]
    done_path: Path
    logs_path: Optional[Path] = None


def run(node_definition: NodeDefinition) -> None:
    logging.basicConfig(
        format="%(asctime)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
        filename=node_definition.logs_path,
        filemode="a",
        level=logging.INFO,
    )
    logger.info(node_definition.model_dump())

    name = node_definition.function_name
    if name == "substitute":
        with open(node_definition.inputs["circuit"], "rb") as fh:
            circuit = Circuit.from_dict(json.loads(fh.read()))

        with open(node_definition.inputs["a"], "rb") as fh:
            a = json.loads(fh.read())

        with open(node_definition.inputs["b"], "rb") as fh:
            b = json.loads(fh.read())

        with open(node_definition.inputs["c"], "rb") as fh:
            c = json.loads(fh.read())

        print(circuit.free_symbols())

        circuit.symbol_substitution({Symbol("a"): a, Symbol("b"): b, Symbol("c"): c})

        with open(node_definition.outputs["circuit"], "w+") as fh:
            fh.write(json.dumps(circuit.to_dict()))

    elif name == "add_measure_all":
        with open(node_definition.inputs["circuit"], "rb") as fh:
            circuit = Circuit.from_dict(json.loads(fh.read()))

        circuit.measure_all()

        with open(node_definition.outputs["circuit"], "w+") as fh:
            fh.write(json.dumps(circuit.to_dict()))

    elif name == "optimise_phase_gadgets":
        with open(node_definition.inputs["circuit"], "rb") as fh:
            circuit = Circuit.from_dict(json.loads(fh.read()))

        Transform.OptimisePhaseGadgets().apply(circuit)

        with open(node_definition.outputs["circuit"], "w+") as fh:
            fh.write(json.dumps(circuit.to_dict()))

    elif name == "expectation":
        with open(node_definition.inputs["backend_result"], "rb") as fh:
            backendresult = BackendResult.from_dict(json.loads(fh.read()))

        expectation = expectation_from_counts(backendresult.get_counts())

        with open(node_definition.outputs["expectation"], "w+") as fh:
            fh.write(json.dumps(expectation))

    # Also important
    else:
        raise ValueError(f"pytket_worker: unknown function: {name}")

    # Very important!
    node_definition.done_path.touch()


def main() -> None:
    node_definition_path = argv[1]
    with open(node_definition_path, "r") as fh:
        node_definition = NodeDefinition(**json.loads(fh.read()))
    run(node_definition)


if __name__ == "__main__":
    main()
