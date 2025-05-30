from typing import Any


annotation_from_schema: dict[str, str] = {
    "integer": "int",
    "number": "float",
    "string": "str",
    "bytes": "bytes",
    "boolean": "bool",
}


def def_key_from_path(path: str) -> str:
    return path.split("/")[-1]


def format_type(v: dict[str, Any]) -> str:
    return (
        def_key_from_path(v["$ref"])
        if "$ref" in v
        else f"TypedValueRef[{annotation_from_schema[v["type"]]}]"
    )


def format_annotated_var(name: str, v: dict[str, Any]) -> str:
    return f"{name}: {format_type(v)}"


def format_model(name: str, props: dict[str, Any]) -> str:
    attrs = [format_annotated_var(k, v) for k, v in props.items()]
    attrs_str = "\n    ".join(attrs)

    return f"""class {name}(BaseModel):
    {attrs_str}
    """


def format_method(name: str, annotations: dict[str, Any]) -> str:
    props = annotations["properties"]
    args = [format_annotated_var(k, v) for k, v in props.items() if k != "return"]
    args_str = ", ".join(args)
    return_type = format_type(props["return"])

    return f"""    @staticmethod
    @abstractmethod
    def {name}({args_str}) -> {return_type}: ...

"""


def format_namespace(name: str, namespace: dict[str, Any]) -> str:
    defs = namespace["$defs"]
    models = [
        format_model(k, v["properties"])
        for k, v in defs.items()
        if "return" not in v["properties"]
    ]
    models_str = "\n".join(models)

    methods = [
        format_method(k, defs[def_key_from_path(v["$ref"])])
        for k, v in namespace["properties"].items()
    ]
    methods_str = "\n".join(methods)

    return f"""from abc import ABC, abstractmethod
from pydantic import BaseModel


{models_str}


class {name}(ABC):
{methods_str}"""
