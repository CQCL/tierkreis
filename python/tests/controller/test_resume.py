from uuid import UUID

from tests.sample_graph import sample_graph
from tierkreis.controller.models import NodeLocation
from tierkreis.controller.resume import resume
from tierkreis.controller.start import start
from tierkreis.controller.storage.filestorage import ControllerFileStorage
from tierkreis.core import Labels
from tierkreis.core.function import FunctionName
from tierkreis.core.protos.tierkreis.v1alpha1.graph import Value, VariantValue
from tierkreis.core.tierkreis_graph import FunctionNode

root_loc = NodeLocation(location=[])


def test_resume_sample_graph():
    g = sample_graph()
    storage = ControllerFileStorage(UUID(int=0))
    storage.clean_graph_files()
    inp_loc = storage.add_input("inp", Value(integer=4))
    vv_loc = storage.add_input(
        "vv", Value(variant=VariantValue("many", Value(integer=2)))
    )
    value_loc = storage.add_input("value", Value(integer=2))

    thunk_loc = storage.add_input(Labels.THUNK, Value(graph=g.to_proto()))
    start(
        storage,
        root_loc,
        FunctionNode(FunctionName("eval")),
        {
            "inp": (inp_loc, "inp"),
            Labels.THUNK: (thunk_loc, Labels.THUNK),
            "vv": (vv_loc, "vv"),
            "value": (value_loc, "value"),
        },
        g.outputs(),
    )

    for _ in range(400):
        resume(storage, root_loc)
        if storage.is_node_finished(root_loc):
            break

    c = storage.read_output(root_loc, "loop_out")
    assert c.integer == 6
