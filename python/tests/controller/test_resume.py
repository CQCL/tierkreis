import json
from time import sleep
from uuid import UUID

import pytest

from tests.sample_graph import sample_graph_without_match, nexus_polling_graph
from tierkreis.controller.models import NodeLocation
from tierkreis.controller.resume import resume
from tierkreis.controller.start import start
from tierkreis.controller.storage.filestorage import ControllerFileStorage
from tierkreis.core import Labels
from tierkreis.core.function import FunctionName
from tierkreis.core.protos.tierkreis.v1alpha1.graph import Value, VariantValue
from tierkreis.core.tierkreis_graph import FunctionNode

from pytket._tket.circuit import Circuit

root_loc = NodeLocation(location=[])


def get_circ_str() -> str:
    """Build a test circuit."""
    circ = Circuit(2, 2)
    circ.Rx(0.2, 0).CX(0, 1).Rz(-0.7, 1).measure_all()
    return json.dumps(circ.to_dict())


def test_resume_sample_graph():
    g = sample_graph_without_match()
    storage = ControllerFileStorage(UUID(int=0))
    storage.clean_graph_files()
    inp_loc = storage.add_input("inp", Value(integer=4))
    vv_loc = storage.add_input(
        "vv", Value(variant=VariantValue("one", Value(integer=2)))
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


@pytest.mark.skip
def test_resume_nexus_polling():
    g = nexus_polling_graph()
    storage = ControllerFileStorage(UUID(int=0))
    storage.clean_graph_files()
    circuit_loc = storage.add_input("circuit", Value(str=get_circ_str()))
    thunk_loc = storage.add_input(Labels.THUNK, Value(graph=g.to_proto()))
    start(
        storage,
        root_loc,
        FunctionNode(FunctionName("eval")),
        {"circuit": (circuit_loc, "circuit"), Labels.THUNK: (thunk_loc, Labels.THUNK)},
        g.outputs(),
    )

    for i in range(400):
        resume(storage, root_loc)
        if storage.is_node_finished(root_loc):
            print(f"break after {i} iterations")
            break
        sleep(1)

    c = storage.read_output(root_loc, "distribution")
    assert "(0, 0)" in json.loads(c.str)
