import logging
from typing import assert_never

from tierkreis.controller.data.graph import NodeDef, PortID, ValueRef
from tierkreis.controller.data.location import Loc
from tierkreis.controller.storage.protocol import ControllerStorage

logger = logging.getLogger(__name__)


def in_edges(node: NodeDef) -> dict[PortID, ValueRef]:
    parents = {k: v for k, v in node.inputs.items()}

    match node.type:
        case "eval":
            parents["body"] = node.graph
        case "loop":
            parents["body"] = node.body
        case "map":
            parents["body"] = node.body
            parents["map_eles"] = (node.input_idx, "map_eles")
        case "ifelse":
            parents["pred"] = node.pred
        case "const" | "function" | "input" | "output":
            pass
        case _:
            assert_never(node)

    return parents


def unfinished_inputs(
    storage: ControllerStorage, loc: Loc, node: NodeDef
) -> list[ValueRef]:
    return [
        x for x in in_edges(node).values() if not storage.is_node_finished(loc.N(x[0]))
    ]
