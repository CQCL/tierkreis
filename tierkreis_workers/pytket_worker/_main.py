import json
import logging
import sys
from sys import argv
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

from pytket._tket.circuit import Circuit

from default_pass import default_compilation_pass

logger = logging.getLogger(__name__)


class NodeDefinition(BaseModel):
    function_name: str
    inputs: dict[str, Path]
    outputs: dict[str, Path]
    done_path: Path
    logs_path: Optional[Path] = None


def compile_circuits(circuits: list[Circuit]) -> list[Circuit]:
    base_pass = default_compilation_pass()
    for circuit in circuits:
        logger.info("CIRCUIT")
        logger.info(circuit.name)
        base_pass.apply(circuit)

    return circuits


def run(node_definition: NodeDefinition):
    logging.basicConfig(
        format="%(asctime)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
        filename=node_definition.logs_path,
        filemode="a",
        level=logging.INFO,
    )
    logger.info(node_definition.model_dump())

    def handle_unhandled_exception(exc_type, exc_value, exc_traceback):
        logger.critical(
            "Unhandled exception", exc_info=(exc_type, exc_value, exc_traceback)
        )

    sys.excepthook = handle_unhandled_exception

    name = node_definition.function_name

    if name == "compile_circuits":
        logger.info("compile_circuits")
        with open(node_definition.inputs["circuits"], "rb") as fh:
            circuit_jsons = json.loads(fh.read())
            assert isinstance(circuit_jsons, list)
            circuits = [Circuit.from_dict(x) for x in circuit_jsons]  # type:ignore

        logger.info("before_compilation")
        compiled_circuits = compile_circuits(circuits)
        logger.info("after_compilation")

        with open(node_definition.outputs["compiled_circuits"], "w+") as fh:
            fh.write(
                json.dumps([x.to_dict() for x in compiled_circuits])  # type:ignore
            )

    elif name == "compile_circuit":
        logger.info("compile_circuit")
        with open(node_definition.inputs["circuit"], "rb") as fh:
            circuit_json = json.loads(fh.read())
            circuit = Circuit.from_dict(circuit_json)  # type:ignore

        logger.info("before_compilation")
        compiled_circuits = compile_circuits([circuit])
        logger.info("after_compilation")

        with open(node_definition.outputs["compiled_circuit"], "w+") as fh:
            fh.write(
                json.dumps(compiled_circuits[0].to_dict())  # type:ignore
            )

    else:
        raise ValueError(f"nexus-worker: unknown function: {name}")

    node_definition.done_path.touch()


def main():
    logger.info("main")
    node_definition_path = argv[1]
    with open(node_definition_path, "r") as fh:
        node_definition = NodeDefinition(**json.loads(fh.read()))
    run(node_definition)


if __name__ == "__main__":
    main()
