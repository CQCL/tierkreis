# /// script
# requires-python = ">=3.12"
# dependencies = ["pydantic"]
# ///
import json
import logging
from sys import argv
from pathlib import Path
from typing import Optional


from pydantic import BaseModel

logger = logging.getLogger(__name__)


class NodeDefinition(BaseModel):
    function_name: str
    inputs: dict[str, Path]
    outputs: dict[str, Path]
    done_path: Path
    error_path: Path
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
    if name == "concat":
        with open(node_definition.inputs["lhs"], "rb") as fh:
            lhs = json.loads(fh.read())

        with open(node_definition.inputs["rhs"], "rb") as fh:
            rhs = json.loads(fh.read())

        value = lhs + rhs

        with open(node_definition.outputs["value"], "w+") as fh:
            fh.write(json.dumps(value))

    # Also important
    else:
        node_definition.error_path.touch()
        raise ValueError(f"string_worker: unknown function: {name}")

    # Very important!
    node_definition.done_path.touch()


def main() -> None:
    node_definition_path = argv[1]
    with open(node_definition_path, "r") as fh:
        node_definition = NodeDefinition(**json.loads(fh.read()))
    run(node_definition)


if __name__ == "__main__":
    main()
