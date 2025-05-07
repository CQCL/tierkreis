from typing import assert_never

from tierkreis.controller.data.graph import NodeDef, PortID, ValueRef


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
        case "const" | "function" | "input" | "output":
            pass
        case _:
            assert_never(node)

    return parents
