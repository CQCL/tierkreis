from pathlib import Path
from typing import Any
from uuid import UUID

import pytest

from tests.controller.sample_graphdata import (
    maps_in_series,
    sample_eval,
    sample_loop,
    sample_map,
)
from tierkreis.controller import run_graph
from tierkreis.controller.data.graph import GraphData
from tierkreis.controller.data.location import Loc
from tierkreis.controller.executor.shell_executor import ShellExecutor
from tierkreis.controller.storage.filestorage import ControllerFileStorage
from tierkreis.core import Labels

params = [
    (sample_eval(), "value", b"12", "sample_eval", 1),
    (sample_loop(), "a", b"10", "sample_loop", 2),
    (
        sample_map(),
        "value",
        b"[6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 34, 36, 38, 40, 42, 44, 46]",
        "sample_map",
        3,
    ),
    (
        maps_in_series(),
        "value",
        b"[0, 4, 8, 12, 16, 20, 24, 28, 32, 36, 40, 44, 48, 52, 56, 60, 64, 68, 72, 76, 80]",
        "maps_in_series",
        4,
    ),
]


@pytest.mark.parametrize(
    "graph,output_port,output,name,id",
    params,
    ids=["sample_eval", "sample_loop", "sample_map", "maps_in_series"],
)
def test_resume_eval(
    graph: GraphData, output_port: str, output: Any, name: str, id: int
):
    g = graph
    storage = ControllerFileStorage(UUID(int=id), name=name)
    executor = ShellExecutor(
        Path("./python/examples/launchers"), logs_path=storage.logs_path
    )
    inputs = {}

    storage.clean_graph_files()
    run_graph(storage, executor, g, inputs)

    c = storage.read_output(Loc(), output_port)
    assert c == output
