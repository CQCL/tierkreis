from pathlib import Path
from uuid import UUID

from tierkreis.controller import run_graph
from tierkreis.controller.data.graph import (
    Const,
    Func,
    GraphData,
    Output,
)
from tierkreis.controller.data.location import Loc
from tierkreis.controller.executor.uv_executor import UvExecutor
from tierkreis.controller.storage.filestorage import ControllerFileStorage
from tierkreis.core import Labels


def coin_toss(const_input: float = 1.0) -> GraphData:
    graph = GraphData()
    threshold = graph.add(Const(const_input))(Labels.VALUE)
    coin_toss = graph.add(Func("coin_toss.toss", {"threshold": threshold}))("coin_toss")
    graph.add(Output({"coin_toss_output": coin_toss}))
    return graph


def test_raise_error():
    g = coin_toss()
    storage = ControllerFileStorage(UUID(int=42), name="coint_toss")
    executor = UvExecutor(Path("./python/tests/errors"), logs_path=storage.logs_path)
    inputs = {}
    storage.clean_graph_files()
    run_graph(storage, executor, g, inputs)

    c = storage.read_output(Loc(), "coin_toss_output")
    assert c == b'{"coin_tossed": true}'
