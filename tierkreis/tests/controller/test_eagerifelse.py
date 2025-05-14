import json
from pathlib import Path
from uuid import UUID

from tierkreis import Labels
from tierkreis.controller.data.graph import (
    Const,
    EagerIfElse,
    Func,
    GraphData,
    Input,
    Output,
)
from tierkreis.controller import run_graph
from tierkreis.controller.data.location import Loc
from tierkreis.controller.executor.uv_executor import UvExecutor
from tierkreis.controller.storage.filestorage import ControllerFileStorage


def eagerifelse_long_running() -> GraphData:
    g = GraphData()
    pred = g.add(Input("pred"))("pred")
    pred_long = g.add(Func("controller.sleep_and_return", {"output": pred}))(
        Labels.VALUE
    )
    one = g.add(Const(1))(Labels.VALUE)
    one_long = g.add(Func("controller.sleep_and_return", {"output": one}))(Labels.VALUE)
    two = g.add(Const(2))(Labels.VALUE)
    out = g.add(EagerIfElse(pred_long, one_long, two))(Labels.VALUE)
    g.add(Output({"simple_eagerifelse_output": out}))
    return g


def test_eagerifelse_long_running():
    g = eagerifelse_long_running()
    storage = ControllerFileStorage(UUID(int=150), name="eagerifelse_long_running")

    registry_path = Path(__file__).parent.parent
    executor = UvExecutor(registry_path=registry_path, logs_path=storage.logs_path)

    storage.clean_graph_files()
    inputs = {"pred": b"true"}
    run_graph(storage, executor, g, inputs)
    actual_output = json.loads(storage.read_output(Loc(), "simple_eagerifelse_output"))
    actual_output == 1
