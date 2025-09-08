import pytest
from tierkreis.exceptions import TierkreisError
from tierkreis.controller.data.graph import GraphData


def test_only_one_output():
    with pytest.raises(TierkreisError):
        g = GraphData()
        g.output({"one": g.const(1)})
        g.output({"two": g.const(2)})
