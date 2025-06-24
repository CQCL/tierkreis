import json
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest

from tests.controller.sample_graphdata import (
    simple_eval,
    simple_loop,
    simple_map,
    factorial,
)
from tierkreis.controller import run_graph
from tierkreis.controller.data.graph import GraphData
from tierkreis.controller.data.location import Loc
from tierkreis.controller.executor.shell_executor import ShellExecutor
from tierkreis.controller.storage.s3storage import S3Storage

factorial_bytes = factorial().model_dump_json().encode()
params = [
    (simple_eval(), 12, "simple_eval", 1, {}),
    (simple_loop(), 10, "simple_loop", 2, {}),
    (simple_map(), list(range(6, 47, 2)), "simple_map", 3, {}),
]
ids = [
    "simple_eval",
    "simple_loop",
    "simple_map",
]


@pytest.mark.parametrize("graph,output,name,id,inputs", params, ids=ids)
def test_s3(graph: GraphData, output: Any, name: str, id: int, inputs: dict[str, Any]):
    g = graph
    storage = S3Storage(
        UUID(int=id),
        name=name,
        endpoint_url="http://localhost:9000",
        access_key_id="minioadmin",
        secret_access_key="minioadmin",
    )
    executor = ShellExecutor(
        Path("./python/examples/launchers"), logs_path=storage.logs_path
    )
    storage.clean_graph_files()
    run_graph(storage, executor, g, inputs)

    output_ports = g.nodes[g.output_idx()].inputs.keys()
    actual_output = {}
    for port in output_ports:
        actual_output[port] = json.loads(storage.read_output(Loc(), port))

    if f"{name}_output" in actual_output:
        assert actual_output[f"{name}_output"] == output
    else:
        assert actual_output == output
