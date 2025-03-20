import json
import os
from pathlib import Path
import stat
from time import sleep
from uuid import UUID


from tests.sample_graph import sample_graph_without_match
from tierkreis.controller.executor.shell_executor import ShellExecutor
from tierkreis.controller.models import NodeLocation
from tierkreis.controller.resume import resume
from tierkreis.controller.start import start
from tierkreis.controller.storage.filestorage import ControllerFileStorage
from tierkreis.core import Labels
from tierkreis.core.function import FunctionName
from tierkreis.core.tierkreis_graph import FunctionNode

root_loc = NodeLocation(location=[])


def test_resume_sample_graph():
    g = sample_graph_without_match()
    workflow_id = UUID(int=0)
    checkpoints_dir = "/tmp/tierkreis/checkpoints"

    checkpoints_path = Path(checkpoints_dir)
    checkpoints_path.mkdir(exist_ok=True, parents=True)
    storage = ControllerFileStorage(
        workflow_id, tierkreis_directory=checkpoints_path
    )

    storage.clean_graph_files()

    err_path = Path(checkpoints_dir) / str(workflow_id) / "logs"
    err_path.mkdir(exist_ok=True, parents=True)
    std_err_path = err_path / "controller_logs"
    std_err_path.touch()
    executor = ShellExecutor(Path("./python/examples/launchers"), std_err_path=std_err_path)

    st = os.stat("./python/examples/launchers/numerical-worker")
    os.chmod("./python/examples/launchers/numerical-worker", st.st_mode | stat.S_IEXEC)

    inp_loc = storage.add_input("inp", json.dumps(4).encode())
    value_loc = storage.add_input("value", json.dumps(2).encode())
    thunk_loc = storage.add_input(Labels.THUNK, g.to_proto().SerializeToString())
    start(
        storage,
        executor,
        root_loc,
        FunctionNode(FunctionName("eval")),
        {
            "inp": (inp_loc, "inp"),
            Labels.THUNK: (thunk_loc, Labels.THUNK),
            "value": (value_loc, "value"),
        },
        g.outputs(),
    )

    for _ in range(400):
        resume(storage, executor, root_loc)
        if storage.is_node_finished(root_loc):
            break
        sleep(0.01)

    c = storage.read_output(root_loc, "loop_out")
    assert c == b"6"
