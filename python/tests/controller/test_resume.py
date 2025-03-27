import json
from pathlib import Path
from uuid import UUID

from tests.sample_graph import sample_graph_without_match
from tierkreis.controller import run_graph
from tierkreis.controller.executor.shell_executor import ShellExecutor
from tierkreis.controller.models import NodeLocation
from tierkreis.controller.storage.filestorage import ControllerFileStorage
from tierkreis.core import Labels


def test_resume_sample_graph():
    g = sample_graph_without_match()
    storage = ControllerFileStorage(UUID(int=0))
    executor = ShellExecutor(
        Path("./python/examples/launchers"), logs_path=storage.logs_path
    )
    inputs = {
        "inp": json.dumps(4).encode(),
        Labels.VALUE: json.dumps(2).encode(),
        Labels.THUNK: g.to_proto().SerializeToString(),
    }

    storage.clean_graph_files()
    run_graph(storage, executor, g, inputs)

    c = storage.read_output(NodeLocation(location=[]), "loop_out")
    assert c == b"6"
