from glob import glob
import json
from logging import getLogger
from pathlib import Path
from sys import argv

from pydantic import BaseModel

logger = getLogger(__name__)


class WorkerCallArgs(BaseModel):
    function_name: str
    inputs: dict[str, Path]
    outputs: dict[str, Path]
    output_dir: Path
    done_path: Path


def iadd(a: int, b: int) -> int:
    logger.debug(f"iadd {a} {b}")
    return a + b


def itimes(a: int, b: int) -> int:
    logger.debug(f"itimes {a} {b}")
    return a * b


def igt(a: int, b: int) -> bool:
    logger.debug(f"igt {a} {b}")
    return a > b


def run(node_definition: WorkerCallArgs):
    logger.debug(node_definition)
    if node_definition.function_name == "iadd":
        with open(node_definition.inputs["a"], "rb") as fh:
            a: int = json.loads(fh.read())
        with open(node_definition.inputs["b"], "rb") as fh:
            b: int = json.loads(fh.read())

        c = iadd(a, b)

        with open(node_definition.outputs["value"], "w+") as fh:
            fh.write(json.dumps(c))

    elif node_definition.function_name == "itimes":
        with open(node_definition.inputs["a"], "rb") as fh:
            a: int = json.loads(fh.read())
        with open(node_definition.inputs["b"], "rb") as fh:
            b: int = json.loads(fh.read())

        c = itimes(a, b)

        with open(node_definition.outputs["value"], "w+") as fh:
            fh.write(json.dumps(c))

    elif node_definition.function_name == "igt":
        with open(node_definition.inputs["a"], "rb") as fh:
            a: int = json.loads(fh.read())
        with open(node_definition.inputs["b"], "rb") as fh:
            b: int = json.loads(fh.read())

        c = igt(a, b)

        with open(node_definition.outputs["value"], "w+") as fh:
            fh.write(json.dumps(c))

    elif node_definition.function_name == "and":
        with open(node_definition.inputs["a"], "rb") as fh:
            a = json.loads(fh.read())
        with open(node_definition.inputs["b"], "rb") as fh:
            b = json.loads(fh.read())

        c = a and b

        with open(node_definition.outputs["value"], "w+") as fh:
            fh.write(json.dumps(c))

    elif node_definition.function_name == "id":
        with open(node_definition.inputs["value"], "rb") as fh:
            value = json.loads(fh.read())

        with open(node_definition.outputs["value"], "w+") as fh:
            fh.write(json.dumps(value))

    elif node_definition.function_name == "fold_values":
        values = []
        inputs = glob(str(node_definition.inputs["values_glob"]))
        inputs.sort(key=lambda p: int(Path(p).name))
        for i, path in enumerate(inputs):
            with open(path, "rb") as fh:
                values.append(json.loads(fh.read()))

        with open(node_definition.outputs["value"], "w+") as fh:
            fh.write(json.dumps(values))

    elif node_definition.function_name == "unfold_values":
        with open(node_definition.inputs["value"], "rb") as fh:
            values_list = json.loads(fh.read())

        if not isinstance(values_list, list):
            raise ValueError("VALUE to unfold must be a list.")

        for i, value in enumerate(values_list):
            with open(node_definition.output_dir / str(i), "w+") as fh:
                fh.write(json.dumps(value))

    else:
        raise ValueError(f"function name {node_definition.function_name} not found")
    node_definition.done_path.touch()


if __name__ == "__main__":
    worker_definition_path = argv[1]
    with open(worker_definition_path, "r") as fh:
        node_definition = WorkerCallArgs(**json.loads(fh.read()))

    run(node_definition)
