from pathlib import Path
from typing import Any, Type
from uuid import UUID

import pytest

from tests.controller.partial_graphdata import double_partial
from tests.controller.sample_graphdata import (
    maps_in_series,
    simple_eagerifelse,
    simple_eval,
    simple_ifelse,
    simple_loop,
    simple_map,
    simple_partial,
)
from tests.controller.loop_graphdata import loop_multiple_acc, loop_multiple_acc_untyped
from tests.controller.typed_graphdata import (
    tuple_untuple,
    typed_destructuring,
    typed_eval,
    typed_loop,
    typed_map,
    factorial,
    gcd,
)
from tierkreis.controller import run_graph
from tierkreis.controller.data.location import Loc
from tierkreis.controller.data.types import PType, ptype_from_bytes
from tierkreis.controller.executor.in_memory_executor import InMemoryExecutor
from tierkreis.controller.executor.shell_executor import ShellExecutor
from tierkreis.controller.storage.filestorage import ControllerFileStorage
from tierkreis.controller.storage.in_memory import ControllerInMemoryStorage
from tierkreis.controller.data.graph import GraphData

params: list[tuple[GraphData, Any, str, int, dict[str, Any]]] = [
    (simple_eval(), 12, "simple_eval", 1, {}),
    (simple_loop(), 10, "simple_loop", 2, {}),
    (simple_map(), list(range(6, 47, 2)), "simple_map", 3, {}),
    (maps_in_series(), list(range(0, 81, 4)), "maps_in_series", 4, {}),
    (simple_ifelse(), 1, "simple_ifelse", 6, {"pred": b"true"}),
    (simple_ifelse(), 2, "simple_ifelse", 7, {"pred": b"false"}),
    (factorial().get_data(), 24, "factorial", 8, {"value": b"4"}),
    (
        loop_multiple_acc_untyped(),
        {"acc1": 6, "acc2": 12, "acc3": 18},
        "multi_acc",
        9,
        {},
    ),
    (
        loop_multiple_acc().get_data(),
        {"acc1": 6, "acc2": 12, "acc3": 18},
        "multi_acc",
        9,
        {},
    ),
    (simple_eagerifelse(), 1, "simple_eagerifelse", 10, {"pred": b"true"}),
    (simple_partial(), 12, "simple_partial", 11, {}),
    (factorial().get_data(), 120, "factorial", 12, {"value": b"5"}),
    (double_partial(), 6, "double_partial", 13, {}),
    (typed_eval().get_data(), 12, "typed_eval", 14, {}),
    (typed_loop().get_data(), 10, "typed_loop", 15, {}),
    (typed_map().get_data(), list(range(6, 47, 2)), "typed_map", 16, {}),
    (typed_destructuring().get_data(), list(range(6, 47, 2)), "typed_map", 17, {}),
    (tuple_untuple().get_data(), 3, "tuple_untuple", 18, {}),
    (gcd().get_data(), 21, "gcd", 19, {"a": 1071, "b": 462}),
    (gcd().get_data(), 2, "gcd", 20, {"a": 12, "b": 26}),
    (gcd().get_data(), 24, "gcd", 21, {"a": 48, "b": 360}),
    (gcd().get_data(), 1, "gcd", 22, {"a": 9357, "b": 5864}),
    (gcd().get_data(), 3, "gcd", 23, {"a": 3, "b": 0}),
]
ids = [
    "simple_eval",
    "simple_loop",
    "simple_map",
    "maps_in_series",
    "simple_ifelse_true",
    "simple_ifelse_false",
    "factorial_4",
    "loop_multiple_acc_untyped",
    "loop_multiple_acc",
    "simple_eagerifelse",
    "simple_partial",
    "factorial_5",
    "double_partial",
    "typed_eval",
    "typed_loop",
    "typed_map",
    "typed_destructuring",
    "tuple_untuple",
    "gcd_1071_462",
    "gcd_12_26",
    "gcd_48_360",
    "gcd_9357_5864",
    "gcd_3_0",
]

storage_classes = [ControllerFileStorage, ControllerInMemoryStorage]
storage_ids = ["FileStorage", "In-memory"]


@pytest.mark.parametrize("storage_class", storage_classes, ids=storage_ids)
@pytest.mark.parametrize("graph,output,name,id,inputs", params, ids=ids)
def test_resume_eval(
    storage_class: Type[ControllerFileStorage | ControllerInMemoryStorage],
    graph: GraphData,
    output: Any,
    name: str,
    id: int,
    inputs: dict[str, PType],
):
    g = graph
    storage = storage_class(UUID(int=id), name=name)
    executor = ShellExecutor(Path("./python/examples/launchers"), Path(""))
    if isinstance(storage, ControllerInMemoryStorage):
        executor = InMemoryExecutor(Path("./tierkreis/tierkreis"), storage=storage)
    storage.clean_graph_files()
    run_graph(storage, executor, g, inputs)

    output_ports = g.nodes[g.output_idx()].inputs.keys()
    actual_output = {}
    for port in output_ports:
        actual_output[port] = ptype_from_bytes(storage.read_output(Loc(), port))

    if f"{name}_output" in actual_output:
        assert actual_output[f"{name}_output"] == output
    elif "value" in actual_output:
        assert actual_output["value"] == output
    else:
        assert actual_output == output
