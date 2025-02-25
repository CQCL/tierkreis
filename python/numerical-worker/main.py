import json
from logging import getLogger
from pathlib import Path
from sys import argv

from pydantic import BaseModel
from tierkreis.core.protos.tierkreis.v1alpha1.graph import Value

logger = getLogger(__name__)


class NodeDefinition(BaseModel):
    function_name: str
    inputs: dict[str, Path]
    outputs: dict[str, Path]
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


if __name__ == "__main__":
    worker_definition_path = argv[1]
    with open(worker_definition_path, "r") as fh:
        node_definition = NodeDefinition(**json.loads(fh.read()))

    if node_definition.function_name == "iadd":
        with open(node_definition.inputs["a"], "rb") as fh:
            a: int = Value.FromString(fh.read()).integer
        with open(node_definition.inputs["b"], "rb") as fh:
            b: int = Value.FromString(fh.read()).integer

        c = iadd(a, b)

        with open(node_definition.outputs["value"], "wb+") as fh:
            fh.write(Value(integer=c).SerializeToString())

    elif node_definition.function_name == "itimes":
        with open(node_definition.inputs["a"], "rb") as fh:
            a: int = Value.FromString(fh.read()).integer
        with open(node_definition.inputs["b"], "rb") as fh:
            b: int = Value.FromString(fh.read()).integer

        c = itimes(a, b)

        with open(node_definition.outputs["value"], "wb+") as fh:
            fh.write(Value(integer=c).SerializeToString())

    elif node_definition.function_name == "igt":
        with open(node_definition.inputs["a"], "rb") as fh:
            a: int = Value.FromString(fh.read()).integer
        with open(node_definition.inputs["a"], "rb") as fh:
            a: int = Value.FromString(fh.read()).integer
        with open(node_definition.inputs["b"], "rb") as fh:
            b: int = Value.FromString(fh.read()).integer

        c = igt(a, b)

        with open(node_definition.outputs["value"], "wb+") as fh:
            fh.write(Value(boolean=c).SerializeToString())

    elif node_definition.function_name == "and":
        with open(node_definition.inputs["a"], "rb") as fh:
            a = Value.FromString(fh.read()).boolean
        with open(node_definition.inputs["b"], "rb") as fh:
            b = Value.FromString(fh.read()).boolean

        c = a and b

        with open(node_definition.outputs["value"], "wb+") as fh:
            fh.write(Value(boolean=c).SerializeToString())

    elif node_definition.function_name == "id":
        with open(node_definition.inputs["value"], "rb") as fh:
            value = Value.FromString(fh.read()).boolean

        with open(node_definition.outputs["value"], "wb+") as fh:
            fh.write(Value(integer=value).SerializeToString())
    else:
        raise ValueError(f"function name {node_definition.function_name} not found")
    node_definition.done_path.touch()
