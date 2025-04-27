from typing import assert_never
from tierkreis.controller.data.graph import NodeDef, ValueRef
from tierkreis.controller.data.location import OutputLoc


def parent_outputs(node: NodeDef) -> set[ValueRef]:
    parents = set(node.inputs.values())

    match node.type:
        case "eval":
            parents.add(node.graph)
        case "loop":
            parents.add(node.body)
        case "map":
            parents.add(node.body)
            parents.add((node.input_idx, "*"))
        case "const" | "function" | "input" | "output":
            pass
        case _:
            assert_never(node)

    return parents
