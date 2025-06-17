import json
from os import environ
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
from tierkreis.controller.executor.kueue_executor import KueueExecutor
from tierkreis.controller.storage.filestorage import ControllerFileStorage

factorial_bytes = factorial().model_dump_json().encode()
params: list[tuple[GraphData, Any, str, int, Any]] = [
    (simple_eval(), 12, "simple_eval", 1, {}),
    (simple_loop(), 10, "simple_loop", 2, {}),
    (simple_map(), list(range(6, 47, 2)), "simple_map", 3, {}),
]
ids = ["simple_eval", "simple_loop", "simple_map"]


@pytest.mark.skipif(environ.get("TEST_K8S") is None, reason="Only works with k8s.")
@pytest.mark.parametrize("graph,output,name,id,inputs", params, ids=ids)
def test_kubernetes(
    graph: GraphData, output: Any, name: str, id: int, inputs: dict[str, Any]
):
    g = graph
    storage = ControllerFileStorage(UUID(int=id), name=name)
    executor = KueueExecutor(storage.logs_path)
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
