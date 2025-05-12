import json
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest

from tests.controller.sample_graphdata import (
    factorial,
    map_with_str_keys,
    maps_in_series,
    simple_eval,
    simple_ifelse,
    simple_loop,
    simple_map,
)
from tests.controller.loop_graphdata import loop_multiple_acc
from tierkreis.controller import run_graph
from tierkreis.controller.data.graph import GraphData
from tierkreis.controller.data.location import Loc
from tierkreis.controller.executor.shell_executor import ShellExecutor
from tierkreis.controller.storage.filestorage import ControllerFileStorage

factorial_bytes = factorial().model_dump_json().encode()
params = [
    (simple_eval(), 12, "simple_eval", 1, {}),
    (simple_loop(), 10, "simple_loop", 2, {}),
    (simple_map(), list(range(6, 47, 2)), "simple_map", 3, {}),
    (maps_in_series(), list(range(0, 81, 4)), "maps_in_series", 4, {}),
    (map_with_str_keys(), {"one": 2, "two": 4, "three": 6}, "map_with_str_keys", 5, {}),
    (simple_ifelse(), 1, "simple_ifelse", 6, {"pred": b"true"}),
    (simple_ifelse(), 2, "simple_ifelse", 7, {"pred": b"false"}),
    (factorial(), 24, "factorial", 8, {"n": b"4", "factorial": factorial_bytes}),
    (factorial(), 120, "factorial", 8, {"n": b"5", "factorial": factorial_bytes}),
    (loop_multiple_acc(), {"acc": 6, "acc2": 12, "acc3": 18}, "multi_acc", 9, {}),
]
ids = [
    "simple_eval",
    "simple_loop",
    "simple_map",
    "maps_in_series",
    "map_with_str_keys",
    "simple_ifelse_true",
    "simple_ifelse_false",
    "factorial_4",
    "factorial_5",
    "loop_multiple_acc",
]


@pytest.mark.parametrize("graph,output,name,id,inputs", params, ids=ids)
def test_resume_eval(
    graph: GraphData, output: Any, name: str, id: int, inputs: dict[str, Any]
):
    g = graph
    storage = ControllerFileStorage(UUID(int=id), name=name)
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
