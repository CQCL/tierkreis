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

worker = Worker("error_worker")


@worker.function()
def fail() -> Value[str]:
    raise Exception("I refuse!")
    return Value(value="I failed to refuse")


def main() -> None:
    node_definition_path = argv[1]
    logger.info(node_definition_path)
    worker.run(Path(node_definition_path))


if __name__ == "__main__":
    logger.info("starting worker")
    main()
