from pathlib import Path
from uuid import UUID

from tests.controller.sample_graphdata import sample_eval, sample_graphdata, sample_map
from tierkreis.controller import run_graph
from tierkreis.controller.data.location import Loc
from tierkreis.controller.executor.shell_executor import ShellExecutor
from tierkreis.controller.storage.filestorage import ControllerFileStorage
from tierkreis.core import Labels


def test_resume_eval():
    g = sample_eval()
    storage = ControllerFileStorage(UUID(int=0))
    executor = ShellExecutor(
        Path("./python/examples/launchers"), logs_path=storage.logs_path
    )
    inputs = {}

    storage.clean_graph_files()
    run_graph(storage, executor, g, inputs)

    c = storage.read_output(Loc(), "value")
    assert c == b"12"


def test_resume_sample_graph():
    g = sample_graphdata()
    storage = ControllerFileStorage(UUID(int=0))
    executor = ShellExecutor(
        Path("./python/examples/launchers"), logs_path=storage.logs_path
    )
    inputs = {}

    storage.clean_graph_files()
    run_graph(storage, executor, g, inputs)

    c = storage.read_output(Loc(), "a")
    assert c == b"10"


def test_resume_sample_map():
    g = sample_map()
    storage = ControllerFileStorage(UUID(int=0))
    executor = ShellExecutor(
        Path("./python/examples/launchers"), logs_path=storage.logs_path
    )
    inputs = {}

    storage.clean_graph_files()
    run_graph(storage, executor, g, inputs)

    c = storage.read_output(Loc(), Labels.VALUE)
    assert (
        c
        == b"[6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 34, 36, 38, 40, 42, 44, 46]"
    )
