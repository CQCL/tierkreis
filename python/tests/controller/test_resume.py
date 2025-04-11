from pathlib import Path
from uuid import UUID

from tests.controller.sample_graphdata import sample_graphdata, sample_map
from tierkreis.controller import run_graph
from tierkreis.controller.data.location import NodeLocation
from tierkreis.controller.executor.shell_executor import ShellExecutor
from tierkreis.controller.storage.filestorage import ControllerFileStorage
from tierkreis.core import Labels


def test_resume_sample_graph():
    g = sample_graphdata()
    storage = ControllerFileStorage(UUID(int=0))
    executor = ShellExecutor(
        Path("./python/examples/launchers"), logs_path=storage.logs_path
    )
    inputs = {Labels.THUNK: g.model_dump_json().encode()}

    storage.clean_graph_files()
    run_graph(storage, executor, g, inputs)

    c = storage.read_output(NodeLocation(location=[]), "a")
    assert c == b"10"


def test_resume_sample_map():
    g = sample_map()
    storage = ControllerFileStorage(UUID(int=0))
    executor = ShellExecutor(
        Path("./python/examples/launchers"), logs_path=storage.logs_path
    )
    inputs = {Labels.THUNK: g.model_dump_json().encode()}

    storage.clean_graph_files()
    run_graph(storage, executor, g, inputs)

    c = storage.read_output(NodeLocation(location=[]), Labels.VALUE)
    assert c == b"[0, 2, 4, 6, 8, 10, 12, 14, 16, 18]"
