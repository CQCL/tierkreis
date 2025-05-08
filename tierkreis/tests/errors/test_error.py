from pathlib import Path
from uuid import UUID

from tierkreis.controller import run_graph
from tierkreis.controller.data.graph import (
    Const,
    Eval,
    Func,
    GraphData,
    Output,
)
from tierkreis.controller.data.location import Loc
from tierkreis.controller.executor.uv_executor import UvExecutor
from tierkreis.controller.storage.filestorage import ControllerFileStorage
from tierkreis import Labels


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


def fail_in_eval() -> GraphData:
    graph = GraphData()
    subgraph_const = graph.add(Const(will_fail()))(Labels.VALUE)
    eval = graph.add(Eval(subgraph_const, {}))
    graph.add(Output({"simple_eval_output": eval("fail")}))
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
