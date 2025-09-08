from pathlib import Path
from uuid import UUID

import pytest
from tests.controller.partial_graphdata import partial_intersection
from tierkreis.controller import run_graph
from tierkreis.controller.data.location import Loc
from tierkreis.controller.executor.uv_executor import UvExecutor
from tierkreis.controller.storage.filestorage import ControllerFileStorage
from tierkreis.exceptions import TierkreisError
from tierkreis.controller.data.graph import GraphData


def will_fail() -> GraphData:
    graph = GraphData()
    out = graph.func("failing_worker.fail", {})("fail")
    graph.output({"fail": out})
    return graph


def wont_fail() -> GraphData:
    graph = GraphData()
    out = graph.func("failing_worker.wont_fail", {})("wont_fail")
    graph.output({"wont_fail": out})
    return graph


def fail_in_eval() -> GraphData:
    graph = GraphData()
    subgraph_const = graph.const(will_fail())
    eval = graph.eval(subgraph_const, {})
    graph.output({"simple_eval_output": eval("fail")})
    return graph


def test_raise_error() -> None:
    g = will_fail()
    storage = ControllerFileStorage(UUID(int=42), name="will_fail")
    executor = UvExecutor(Path(__file__).parent, logs_path=storage.logs_path)
    storage.clean_graph_files()
    run_graph(storage, executor, g, {}, n_iterations=1000)
    assert storage.node_has_error(Loc("-.N0"))


def test_raises_no_error() -> None:
    g = wont_fail()
    storage = ControllerFileStorage(UUID(int=43), name="wont_fail")
    executor = UvExecutor(Path(__file__).parent, logs_path=storage.logs_path)
    storage.clean_graph_files()
    run_graph(storage, executor, g, {}, n_iterations=100)
    assert not storage.node_has_error(Loc("-.N0"))


def test_nested_error() -> None:
    g = fail_in_eval()
    storage = ControllerFileStorage(UUID(int=44), name="eval_will_fail")
    executor = UvExecutor(Path(__file__).parent, logs_path=storage.logs_path)
    storage.clean_graph_files()
    run_graph(storage, executor, g, {}, n_iterations=1000)
    assert (storage.logs_path.parent / "-/errors").exists()


def test_partial_graph_intersection() -> None:
    with pytest.raises(TierkreisError):
        g = partial_intersection()
        storage = ControllerFileStorage(UUID(int=45), name="partial_intersection_fails")
        executor = UvExecutor(Path(__file__).parent, logs_path=storage.logs_path)
        storage.clean_graph_files()
        run_graph(storage, executor, g, {}, n_iterations=1000)
        assert (storage.logs_path.parent / "-/errors").exists()
