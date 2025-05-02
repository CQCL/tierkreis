import json
import logging
import time
from pathlib import Path
from random import random
from sys import argv

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class NodeDefinition(BaseModel):
    function_name: str
    inputs: dict[str, Path]
    outputs: dict[str, Path]
    done_path: Path
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

    logger.info("Starting work by sleeping...")
    time.sleep(5)
    logger.info("See if we succeed")
    with open(node_definition.inputs["threshold"], "rb") as fh:
        threshold = json.load(fh)
        assert isinstance(threshold, float or int)

    if random() > threshold:
        logger.error("Bad luck, raising an error now...")
        raise ValueError("No bad luck allowed here!")
    logger.info("Seems like nothing bad happened.")
    with open(node_definition.outputs["coin_toss"], "w+") as fh:
        json.dump({"coin_tossed": True}, fh)
    node_definition.done_path.touch()


def main() -> None:
    logger.info("main")
    node_definition_path = argv[1]
    with open(node_definition_path, "r") as fh:
        node_definition = NodeDefinition(**json.loads(fh.read()))
    run(node_definition)


if __name__ == "__main__":
    main()
