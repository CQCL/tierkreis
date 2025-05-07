from pathlib import Path
from uuid import UUID

from tierkreis.controller import run_graph
from tierkreis.controller.data.graph import (
    Func,
    GraphData,
    Output,
)
from tierkreis.controller.data.location import Loc
from tierkreis.controller.executor.uv_executor import UvExecutor
from tierkreis.controller.storage.filestorage import ControllerFileStorage


def will_fail() -> GraphData:
    graph = GraphData()
    out = graph.add(Func("failing_worker.fail", {}))("fail")
    graph.add(Output({"fail": out}))
    return graph


def wont_fail() -> GraphData:
    graph = GraphData()
    out = graph.add(Func("failing_worker.wont_fail", {}))("wont_fail")
    graph.add(Output({"wont_fail": out}))
    return graph


def test_raise_error() -> None:
    g = will_fail()
    storage = ControllerFileStorage(UUID(int=42), name="will_fail")
    executor = UvExecutor(Path("./python/tests/errors"), logs_path=storage.logs_path)
    storage.clean_graph_files()
    run_graph(storage, executor, g, {}, n_iterations=20, polling_interval_seconds=0.5)
    error_path = storage.logs_path.parent / "-.N0/errors"
    assert storage.node_has_error(Loc("-.N0"))
    assert error_path.read_text().startswith("Traceback (most recent call last):")


def test_raises_no_error() -> None:
    g = wont_fail()
    storage = ControllerFileStorage(UUID(int=43), name="wont_fail")
    executor = UvExecutor(Path("./python/tests/errors"), logs_path=storage.logs_path)
    storage.clean_graph_files()
    run_graph(storage, executor, g, {}, n_iterations=100)
    assert not storage.node_has_error(Loc("-.N0"))
