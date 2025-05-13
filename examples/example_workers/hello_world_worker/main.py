# /// script
# requires-python = ">=3.12"
# dependencies = ["pydantic", "tierkreis"]
#
# [tool.uv.sources]
# tierkreis = { path = "../../../tierkreis", editable = true }
# ///
import logging
from sys import argv
from pathlib import Path


from tierkreis import Worker, Value

logger = logging.getLogger(__name__)

worker = Worker("hello_world_worker")


@worker.function()
def greet(greeting: str, subject: str) -> Value[str]:
    logger.info("%s %s", greeting, subject)
    return Value(value=greeting + subject)


def main() -> None:
    node_definition_path = argv[1]
    logger.info(node_definition_path)
    worker.run(Path(node_definition_path))


if __name__ == "__main__":
    logger.info("starting worker")
    main()
