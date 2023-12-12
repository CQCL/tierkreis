import pytest
from sample_graph import sample_graph as sample_g

from tierkreis.core.tierkreis_graph import TierkreisEdge, TierkreisGraph
from tierkreis.core.values import TierkreisValue, VariantValue
from tierkreis.pyruntime import PyRuntime


@pytest.fixture()
def sample_graph() -> TierkreisGraph:
    return sample_g()


@pytest.mark.asyncio
async def test_callback(sample_graph: TierkreisGraph, pyruntime_function: PyRuntime):
    ins = {"inp": "world", "vv": VariantValue("many", TierkreisValue.from_python(2))}

    cache = {}

    def cback(e: TierkreisEdge, v: TierkreisValue):
        cache[e] = v

    pyruntime_function.set_callback(cback)
    outs = await pyruntime_function.run_graph(sample_graph, **ins)
    assert all(e in cache for e in sample_graph.edges())
    assert sorted(outs) == sorted(sample_graph.outputs())
