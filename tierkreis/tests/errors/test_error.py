from pathlib import Path
from uuid import UUID

import pytest
from tests.controller.partial_graphdata import partial_intersection
from tierkreis.builder import GraphBuilder
from tierkreis.controller import run_graph
from tierkreis.controller.data.core import EmptyModel
from tierkreis.controller.data.location import Loc
from tierkreis.controller.data.models import TKR
from tierkreis.controller.executor.uv_executor import UvExecutor
from tierkreis.controller.storage.filestorage import ControllerFileStorage
from tierkreis.exceptions import TierkreisError
from tests.errors.failing_worker.stubs import fail, wont_fail, exit_code_1


def will_fail_graph():
    graph = GraphBuilder(EmptyModel, TKR[int])
    graph.outputs(graph.task(fail()))
    return graph


def wont_fail_graph():
    graph = GraphBuilder(EmptyModel, TKR[int])
    graph.outputs(graph.task(wont_fail()))
    return graph


def fail_in_eval():
    graph = GraphBuilder(EmptyModel, TKR[int])
    graph.outputs(graph.eval(will_fail_graph(), EmptyModel()))
    return graph


def non_zero_exit_code():
    graph = GraphBuilder(EmptyModel, TKR[int])
    graph.outputs(graph.task(exit_code_1()))
    return graph


def test_raise_error() -> None:
    g = will_fail_graph()
    storage = ControllerFileStorage(UUID(int=42), name="will_fail")
    executor = UvExecutor(Path(__file__).parent, logs_path=storage.logs_path)
    storage.clean_graph_files()
    run_graph(storage, executor, g.get_data(), {}, n_iterations=1000)
    assert storage.node_has_error(Loc("-.N0"))


def test_raises_no_error() -> None:
    g = wont_fail_graph()
    storage = ControllerFileStorage(UUID(int=43), name="wont_fail")
    executor = UvExecutor(Path(__file__).parent, logs_path=storage.logs_path)
    storage.clean_graph_files()
    run_graph(storage, executor, g.get_data(), {}, n_iterations=100)
    assert not storage.node_has_error(Loc("-.N0"))


def test_nested_error() -> None:
    g = fail_in_eval()
    storage = ControllerFileStorage(UUID(int=44), name="eval_will_fail")
    executor = UvExecutor(Path(__file__).parent, logs_path=storage.logs_path)
    storage.clean_graph_files()
    run_graph(storage, executor, g.get_data(), {}, n_iterations=1000)
    assert (storage.logs_path.parent / "-/errors").exists()


def test_partial_graph_intersection() -> None:
    with pytest.raises(TierkreisError):
        g = partial_intersection()
        storage = ControllerFileStorage(UUID(int=45), name="partial_intersection_fails")
        executor = UvExecutor(Path(__file__).parent, logs_path=storage.logs_path)
        storage.clean_graph_files()
        run_graph(storage, executor, g, {}, n_iterations=1000)
        assert (storage.logs_path.parent / "-/errors").exists()


def test_non_zero_exit_code() -> None:
    g = non_zero_exit_code()
    storage = ControllerFileStorage(UUID(int=46), name="non_zero_exit_code")
    executor = UvExecutor(Path(__file__).parent, logs_path=storage.logs_path)
    storage.clean_graph_files()
    run_graph(storage, executor, g.get_data(), {}, n_iterations=1000)
    assert (storage.logs_path.parent / "-/_error").exists()
