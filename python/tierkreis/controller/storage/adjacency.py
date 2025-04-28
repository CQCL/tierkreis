from typing import assert_never
from tierkreis.controller.data.graph import NodeDef, PortID, ValueRef


def in_edges(node: NodeDef) -> dict[PortID, ValueRef]:
    parents = node.inputs

    match node.type:
        case "eval":
            parents["graph"] = node.graph
        case "loop":
            parents["body"] = node.body
        case "map":
            parents["body"] = node.body
            parents["*"] = (node.input_idx, "*")
        case "const" | "function" | "input" | "output":
            pass
        case _:
            assert_never(node)

    return parents
