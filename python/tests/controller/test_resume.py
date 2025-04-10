from pathlib import Path
from uuid import UUID

from tests.controller.test_data import k
from tierkreis.controller import run_graph
from tierkreis.controller.executor.shell_executor import ShellExecutor
from tierkreis.controller.data.location import NodeLocation
from tierkreis.controller.storage.filestorage import ControllerFileStorage
from tierkreis.core import Labels


def test_resume_sample_graph():
    g = k()
    storage = ControllerFileStorage(UUID(int=0))
    executor = ShellExecutor(
        Path("./python/examples/launchers"), logs_path=storage.logs_path
    )
    inputs = {Labels.THUNK: g.model_dump_json().encode()}

    storage.clean_graph_files()
    run_graph(storage, executor, g, inputs)

    c = storage.read_output(NodeLocation(location=[]), "a")
    assert c == b"10"
