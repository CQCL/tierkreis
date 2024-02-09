from typing import cast

import pytest
from pytket.backends.backendresult import BackendResult

from tierkreis import TierkreisGraph
from tierkreis.common_types.circuit import register_pytket_types
from tierkreis.core.values import StructValue, VecValue
from tierkreis.pyruntime import PyRuntime

register_pytket_types()


@pytest.fixture
def bell_circuit() -> str:
    return (
        r'{"bits": [["c", [0]], ["c", [1]]], "commands": [{"args": [["q", [0]]], "op": '
        r'{"type": "H"}}, {"args": [["q", [0]], ["q", [1]]], "op": {"type": "CX"}}, '
        r'{"args": [["q", [0]], ["c", [0]]], "op": {"type": "Measure"}}, {"args": '
        r'[["q", [1]], ["c", [1]]], "op": {"type": "Measure"}}], '
        r'"implicit_permutation": [[["q", [0]], ["q", [0]]], [["q", [1]], ["q", '
        r'[1]]]], "phase": "0.0", "qubits": [["q", [0]], ["q", [1]]]}'
    )


@pytest.fixture
def pytket_pyruntime():
    import pytket_worker.main  # type: ignore

    return PyRuntime([pytket_worker.main.root])


@pytest.mark.asyncio
@pytest.mark.pytket
async def test_compile_circuit(bell_circuit: str, pytket_pyruntime) -> None:
    tg = TierkreisGraph()
    load_node = tg.add_func("pytket::load_circuit_json", json_str=tg.input["input"])
    compile_node = tg.add_func(
        "pytket::compile_circuits",
        circuits=tg.make_vec([load_node["value"]]),
        pass_name=tg.add_const("FullPeepholeOptimise"),
    )
    tg.set_outputs(out=compile_node)

    outs = await pytket_pyruntime.run_graph(tg, input=bell_circuit)

    assert isinstance(cast(VecValue, outs["out"]).values[0], StructValue)


@pytest.mark.asyncio
@pytest.mark.pytket
async def test_execute_circuit(bell_circuit: str, pytket_pyruntime) -> None:
    tg = TierkreisGraph()
    vec_elems = tg.vec_last_n_elems(tg.input["circuits"], 2)
    load_node1 = tg.add_func("pytket::load_circuit_json", json_str=vec_elems[0])
    load_node2 = tg.add_func("pytket::load_circuit_json", json_str=vec_elems[1])
    execute_node = tg.add_func(
        "pytket::execute_circuits",
        circuits=tg.make_vec([load_node1, load_node2]),
        shots=tg.input["shots"],
        backend_name=tg.add_const("AerBackend"),
    )
    tg.set_outputs(out=execute_node)

    shots = [10, 20]
    outputs = cast(
        VecValue,
        (
            await pytket_pyruntime.run_graph(
                tg,
                circuits=[bell_circuit, bell_circuit],
                shots=shots,
            )
        )["out"],
    )

    for count, res in zip(shots, outputs.values):
        assert isinstance(res, StructValue)

        pytket_res = res.to_python(BackendResult)

        assert sum(pytket_res.get_counts().values()) == count
