import logging
from pathlib import Path
from typing import Any
from pydantic import BaseModel, PydanticSchemaGenerationError, create_model
from tierkreis.exceptions import TierkreisError
from tierkreis.worker.codegen import format_schema
from tierkreis.worker.models import Namespace
from tierkreis.worker.worker import Worker

logger = logging.getLogger(__name__)
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


def schema_from_namespace(name: str, namespace: Namespace) -> dict[str, Any]:
    models: dict[str, Any] = {}
    for k, f in namespace.items():
        try:
            for _, annotation in f.items():
                schema_from_annotation(annotation)
            models[k] = create_model(k, **f)
        except (PydanticSchemaGenerationError, TierkreisError):
            logger.warning(f"Cannot generate schema from {k} {f}.")
            continue

    X = create_model(name, **models)
    return X.model_json_schema()


def write_schema(worker: Worker, out_path: Path) -> None:
    with open(out_path, "w+") as fh:
        schema = schema_from_namespace(worker.name, worker.namespace)
        contents = format_schema(worker.name, schema)
        fh.write(contents)
