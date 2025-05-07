import json
import logging
from pathlib import Path
from sys import argv
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class NodeDefinition(BaseModel):
    function_name: str
    inputs: dict[str, Path]
    outputs: dict[str, Path]
    done_path: Path
    error_path: Path
    logs_path: Path | None = None


def run(node_definition: NodeDefinition) -> None:
    logging.basicConfig(
        format="%(asctime)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
        filename=node_definition.logs_path,
        filemode="a",
        level=logging.INFO,
    )
    logger.info(node_definition.model_dump())
    logger.info("Doing some work...")
    logger.info(f"function name: {node_definition.function_name}")
    name = node_definition.function_name
    if name == "fail":
        logger.error("Raising an error now...")
        node_definition.error_path.touch()
        raise ValueError("Worker failed!")

    with open(node_definition.outputs["wont_fail"], "w+") as fh:
        json.dump({"wont_fail": True}, fh)
    node_definition.done_path.touch()


def main() -> None:
    logger.info("main")
    node_definition_path = argv[1]
    with open(node_definition_path, "r") as fh:
        node_definition = NodeDefinition(**json.loads(fh.read()))
    run(node_definition)


if __name__ == "__main__":
    main()
