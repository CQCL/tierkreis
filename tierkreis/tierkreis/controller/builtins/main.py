import json
import logging
from glob import glob
from logging import getLogger
from pathlib import Path
from sys import argv
from typing import Any

from pydantic import BaseModel

logger = getLogger(__name__)


class WorkerCallArgs(BaseModel):
    function_name: str
    inputs: dict[str, Path]
    outputs: dict[str, Path]
    output_dir: Path
    done_path: Path
    error_path: Path
    logs_path: Path | None


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
    logging.basicConfig(
        format="%(asctime)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
        filename=node_definition.logs_path,
        filemode="a",
        level=logging.INFO,
    )
    logger.info(node_definition.model_dump())
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

    elif node_definition.function_name == "fold_dict":
        values = {}
        inputs = glob(str(node_definition.inputs["values_glob"]))
        for path in inputs:
            with open(path, "rb") as fh:
                k = Path(path).name
                values[k] = json.loads(fh.read())

        with open(node_definition.outputs["value"], "w+") as fh:
            fh.write(json.dumps(values))

    elif node_definition.function_name == "unfold_dict":
        with open(node_definition.inputs["value"], "rb") as fh:
            values_dict = json.loads(fh.read())

        if not isinstance(values_dict, dict):
            raise ValueError("VALUE to unfold must be a dict.")

        for k, value in values_dict.items():
            with open(node_definition.output_dir / k, "w+") as fh:
                fh.write(json.dumps(value))

    elif node_definition.function_name == "append":
        with open(node_definition.inputs["l"], "rb") as fh:
            list_l = json.loads(fh.read())

        with open(node_definition.inputs["a"], "rb") as fh:
            a = json.loads(fh.read())

        assert isinstance(list_l, list)
        new_l: list[Any] = list_l + [a]

        with open(node_definition.outputs["value"], "w+") as fh:
            fh.write(json.dumps(new_l))

    elif node_definition.function_name == "head":
        with open(node_definition.inputs["l"], "rb") as fh:
            list_l = json.loads(fh.read())

        assert isinstance(list_l, list)
        head, rest = list_l[0], list_l[1:]

        with open(node_definition.outputs["head"], "w+") as fh:
            fh.write(json.dumps(head))

        with open(node_definition.outputs["rest"], "w+") as fh:
            fh.write(json.dumps(rest))

    elif node_definition.function_name == "len":
        with open(node_definition.inputs["l"], "rb") as fh:
            list_l = json.loads(fh.read())

        length = len(list_l)
        logger.info(f"LEN {length}")

        with open(node_definition.outputs["value"], "w+") as fh:
            fh.write(json.dumps(length))

    elif node_definition.function_name == "str_eq":
        with open(node_definition.inputs["a"], "rb") as fh:
            str_a = json.loads(fh.read())

        with open(node_definition.inputs["b"], "rb") as fh:
            str_b = json.loads(fh.read())

        ans = str_a == str_b

        with open(node_definition.outputs["value"], "w+") as fh:
            fh.write(json.dumps(ans))

    elif node_definition.function_name == "str_neq":
        with open(node_definition.inputs["a"], "rb") as fh:
            str_a = json.loads(fh.read())

        with open(node_definition.inputs["b"], "rb") as fh:
            str_b = json.loads(fh.read())

        ans = str_a != str_b

        with open(node_definition.outputs["value"], "w+") as fh:
            fh.write(json.dumps(ans))

    elif node_definition.function_name == "zip":
        with open(node_definition.inputs["a"], "rb") as fh:
            list_a = json.loads(fh.read())

        with open(node_definition.inputs["b"], "rb") as fh:
            list_b = json.loads(fh.read())

        ans = list(zip(list_a, list_b))

        with open(node_definition.outputs["value"], "w+") as fh:
            fh.write(json.dumps(ans))

    elif node_definition.function_name == "unzip":
        with open(node_definition.inputs["value"], "rb") as fh:
            value: list[tuple[object, object]] = json.loads(fh.read())

        list_a, list_b = map(list, zip(*value))

        with open(node_definition.outputs["a"], "w+") as fh:
            fh.write(json.dumps(list_a))

        with open(node_definition.outputs["b"], "w+") as fh:
            fh.write(json.dumps(list_b))

    else:
        raise ValueError(f"function name {node_definition.function_name} not found")
    node_definition.done_path.touch()


if __name__ == "__main__":
    worker_definition_path = argv[1]
    with open(worker_definition_path, "r") as fh:
        node_definition = WorkerCallArgs(**json.loads(fh.read()))

    run(node_definition)
