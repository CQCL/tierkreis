"""Simple utilities useful throughout the codebase."""
from typing import Callable, Mapping, Optional, TypeVar, Union

from tierkreis.core.function import FunctionDeclaration, FunctionName
from tierkreis.core.tierkreis_graph import TierkreisGraph

K = TypeVar("K")
V = TypeVar("V")
W = TypeVar("W")


def map_vals(inp: Mapping[K, V], f: Callable[[V], W]) -> dict[K, W]:
    return {k: f(v) for k, v in inp.items()}


def rename_ports_graph(name_map: dict[str, str]) -> TierkreisGraph:
    """Generate an identity graph with inputs -> outputs mapped by the provided
    dictionary."""
    tg = TierkreisGraph()

    tg.set_outputs(**{out: tg.input[inp] for inp, out in name_map.items()})

    return tg


def graph_from_func(
    name: Union[str, FunctionName],
    func: FunctionDeclaration,
    input_map: Optional[dict[str, str]] = None,
    output_map: Optional[dict[str, str]] = None,
) -> TierkreisGraph:
    """Build a graph with a single function node.
    If (input_map/output_map) is provided keys of the map which are
    (inputs/outputs) to the function
    are connected to the value as the (input/output) to the graph.
    For any missing keys, the same port name as the function is used.
    """
    inmap = input_map or {}
    oumap = output_map or {}

    for mp, order in [(inmap, func.input_order), (oumap, func.output_order)]:
        for port in order:
            if port not in mp:
                mp[port] = port

    tg = TierkreisGraph()
    node = tg.add_func(name, **{k: tg.input[v] for (k, v) in inmap.items()})
    tg.set_outputs(**{v: node[k] for k, v in oumap.items()})
    return tg
