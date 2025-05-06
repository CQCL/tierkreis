import json
from typing import Any
from uuid import UUID

import pytest

from tests.controller.sample_graphdata import (
    map_with_str_keys,
    maps_in_series,
    simple_eval,
    simple_loop,
    simple_map,
)
from tierkreis.controller import run_graph
from tierkreis.controller.data.graph import GraphData
from tierkreis.controller.data.location import Loc
from tierkreis.controller.storage.filestorage import ControllerFileStorage

params = [
    (simple_eval(), 12, "simple_eval", 1),
    (simple_loop(), 10, "simple_loop", 2),
    (
        simple_map(),
        [
            6,
            8,
            10,
            12,
            14,
            16,
            18,
            20,
            22,
            24,
            26,
            28,
            30,
            32,
            34,
            36,
            38,
            40,
            42,
            44,
            46,
        ],
        "simple_map",
        3,
    ),
    (
        maps_in_series(),
        [
            0,
            4,
            8,
            12,
            16,
            20,
            24,
            28,
            32,
            36,
            40,
            44,
            48,
            52,
            56,
            60,
            64,
            68,
            72,
            76,
            80,
        ],
        "maps_in_series",
        4,
    ),
    (map_with_str_keys(), {"one": 2, "two": 4, "three": 6}, "map_with_str_keys", 5),
]
ids = [
    "simple_eval",
    "simple_loop",
    "simple_map",
    "maps_in_series",
    "map_with_str_keys",
]


@pytest.mark.parametrize("graph,output,name,id", params, ids=ids)
def test_resume_eval(graph: GraphData, output: Any, name: str, id: int):
    g = graph
    storage = ControllerFileStorage(UUID(int=id), name=name)
    executor = None
    inputs = {}

    storage.clean_graph_files()
    run_graph(storage, executor, g, inputs)

    c = json.loads(storage.read_output(Loc(), f"{name}_output"))
    assert c == output
