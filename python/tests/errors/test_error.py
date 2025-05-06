from pathlib import Path
from uuid import UUID

from tierkreis.controller import run_graph
from tierkreis.controller.data.graph import (
    Func,
    GraphData,
)
from tierkreis.controller.executor.uv_executor import UvExecutor
from tierkreis.controller.storage.filestorage import ControllerFileStorage



def will_fail() -> GraphData:
    graph = GraphData()
    graph.add(Func("failing_worker.fail", {}))("fail")
    return graph


def test_raise_error():
    g = will_fail()
    storage = ControllerFileStorage(UUID(int=42), name="will_fail")
    executor = UvExecutor(Path("./python/tests/errors"), logs_path=storage.logs_path)
    storage.clean_graph_files()
    run_graph(storage, executor, g, {}, n_iterations=10)
    error_path = storage.logs_path.parent / "-.N0/errors"
    assert error_path.exists()
