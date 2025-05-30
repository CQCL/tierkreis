from typing import Any
from pydantic import BaseModel
from tierkreis.exceptions import TierkreisError
from tierkreis.worker.models import Annotations, Namespace

schema_from_type: dict[type, str] = {
    int: "integer",
    float: "number",
    str: "string",
    bytes: "bytes",  # Not standard JSON schema.
    bool: "boolean",
}


def schema_from_annotation(annotation: Any) -> dict[str, Any]:
    if annotation in schema_from_type:
        return {"type": schema_from_type[annotation]}

    if issubclass(annotation, BaseModel):
        return annotation.model_json_schema()

    raise TierkreisError(f"type {annotation} is not supported")


def schema_from_annotations(annotations: Annotations) -> dict[str, Any]:
    schema: dict[str, Any] = {}
    for k, v in annotations.items():
        schema[k] = schema_from_annotation(v)
    return schema


def schema_from_namespace(namespace: Namespace) -> dict[str, Any]:
    schema: dict[str, Any] = {}
    for k, v in namespace.items():
        schema[k] = schema_from_annotations(v)
    return schema
