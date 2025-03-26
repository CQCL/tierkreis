import json
from pathlib import Path
from time import sleep
from uuid import UUID

from tests.sample_graph import sample_graph_without_match
from tierkreis.controller.executor.shell_executor import ShellExecutor
from tierkreis.controller.models import NodeLocation
from tierkreis.controller.resume import resume
from tierkreis.controller.start import NodeRunData, start
from tierkreis.controller.storage.filestorage import ControllerFileStorage
from tierkreis.core import Labels
from tierkreis.core.function import FunctionName
from tierkreis.core.tierkreis_graph import FunctionNode

root_loc = NodeLocation(location=[])


def test_resume_sample_graph():
    g = sample_graph_without_match()
    storage = ControllerFileStorage(UUID(int=0))
    executor = ShellExecutor(
        Path("./python/examples/launchers"), logs_path=storage.logs_path
    )

    storage.clean_graph_files()
    inp_loc = storage.add_input("inp", json.dumps(4).encode())
    value_loc = storage.add_input("value", json.dumps(2).encode())
    thunk_loc = storage.add_input(Labels.THUNK, g.to_proto().SerializeToString())
    start(
        storage,
        executor,
        NodeRunData(
            root_loc,
            FunctionNode(FunctionName("eval")),
            {
                "inp": (inp_loc, "inp"),
                Labels.THUNK: (thunk_loc, Labels.THUNK),
                "value": (value_loc, "value"),
            },
            g.outputs(),
        ),
    )

    for _ in range(400):
        resume(storage, executor, root_loc)
        if storage.is_node_finished(root_loc):
            break
        sleep(0.01)

    c = storage.read_output(root_loc, "loop_out")
    assert c == b"6"
