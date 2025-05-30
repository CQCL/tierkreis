from typing import Any
from pydantic import PydanticSchemaGenerationError, create_model
from tierkreis.exceptions import TierkreisError
from tierkreis.worker.codegen import format_namespace
from tierkreis.controller.builtins.main import worker
from tierkreis.worker.schema import schema_from_annotation


def test_schema():
    models: dict[str, Any] = {}
    for k, f in worker.namespace.items():
        try:
            for _, annotation in f.items():
                schema_from_annotation(annotation)
            models[k] = create_model(k, **f)
        except (PydanticSchemaGenerationError, TierkreisError):
            print(k, f)
            continue

    X = create_model("X", **models)
    nsp = X.model_json_schema()
    worker.namespace
    hints = format_namespace("Builtins", nsp)
    print(hints)
    assert False
