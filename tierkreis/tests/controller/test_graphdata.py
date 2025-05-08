import pytest
from tierkreis.controller.data.graph import Const, GraphData, Output
from tierkreis.exceptions import TierkreisError
from tierkreis.labels import Labels


def test_only_one_output():
    with pytest.raises(TierkreisError):
        g = GraphData()
        g.add(Output({"one": g.add(Const(1))(Labels.VALUE)}))
        g.add(Output({"two": g.add(Const(2))(Labels.VALUE)}))
