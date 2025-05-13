import pytest

from tierkreis.cli.tkr import load_graph, _load_inputs
from tierkreis.controller.data.graph import GraphData
from tierkreis.exceptions import TierkreisError

from tests.controller.sample_graphdata import simple_eval

simple_eval_graph = simple_eval()

graph_params = [
    ("tests.controller.sample_graphdata:simple_eval", simple_eval_graph),
    ("tierkreis/tests/controller/sample_graphdata.py:simple_eval", simple_eval_graph),
]


@pytest.mark.parametrize("input,graph", graph_params)
def test_load_graph(input: str, graph: GraphData) -> None:
    assert load_graph(input) == graph


def test_load_graph_invalid() -> None:
    with pytest.raises(FileNotFoundError):
        load_graph("sample_graphdata.py:simple_eval")
    with pytest.raises(ModuleNotFoundError):
        load_graph("sample_graphdata:simple_eval")
    with pytest.raises(TierkreisError):
        load_graph(["invalid_arg"])
    with pytest.raises(TierkreisError):
        load_graph(["at_least_a:colon"])


input_params = [
    (
        ["tierkreis/tests/cli/data/data.json"],
        {
            "a_string": b'"string"',
            "a_value": b"5",
        },
    ),
    (
        [
            "input1:tierkreis/tests/cli/data/input1",
            "input2:tierkreis/tests/cli/data/input2",
        ],
        {"input1": b"test", "input2": b'{"a": 5, "b": "string"}'},
    ),
]


@pytest.mark.parametrize("input,result", input_params)
def test_load_inputs(input: list[str], result: dict[str, bytes]) -> None:
    assert _load_inputs(input) == result


def test_load_inputs_invalid() -> None:
    with pytest.raises(FileNotFoundError):
        _load_inputs(["data.json"])
    with pytest.raises(FileNotFoundError):
        _load_inputs(["at_least_a:colon"])
    with pytest.raises(TierkreisError):
        _load_inputs(["wrong_format"])


def test_end_to_end() -> None:
    pass
