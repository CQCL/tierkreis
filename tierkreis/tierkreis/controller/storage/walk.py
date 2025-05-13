import json
from dataclasses import dataclass, field
from logging import getLogger
from typing import assert_never

from tierkreis.controller.consts import BODY_PORT
from tierkreis.controller.data.graph import (
    Eval,
    GraphData,
    Loop,
    Map,
    NodeDef,
    NodeIndex,
)
from tierkreis.controller.data.location import Loc, NodeRunData
from tierkreis.controller.storage.adjacency import unfinished_inputs
from tierkreis.controller.storage.protocol import ControllerStorage
from tierkreis.labels import Labels

logger = getLogger(__name__)


@dataclass
class WalkResult:
    inputs_ready: list[NodeRunData]
    started: list[Loc]
    errored: list[Loc] = field(default_factory=list)

    def extend(self, walk_result: "WalkResult") -> None:
        self.inputs_ready.extend(walk_result.inputs_ready)
        self.started.extend(walk_result.started)
        self.errored.extend(walk_result.errored)


def unfinished_results(
    result: WalkResult,
    storage: ControllerStorage,
    parent: Loc,
    node: NodeDef,
    graph: GraphData,
) -> int:
    unfinished = unfinished_inputs(storage, parent, node)
    [result.extend(walk_node(storage, parent, x[0], graph)) for x in unfinished]
    return len(unfinished)


def walk_node(
    storage: ControllerStorage, parent: Loc, idx: NodeIndex, graph: GraphData
) -> WalkResult:
    """Should only be called when a node has not finished."""
    loc = parent.N(idx)
    if storage.node_has_error(loc):
        logger.error(f"Node {loc} has encountered an error:")
        logger.error(f"\n\n{storage.read_errors(loc)}\n\n")
        return WalkResult([], [], [loc])

    node = graph.nodes[idx]
    node_run_data = NodeRunData(loc, node, list(graph.outputs[idx]))
    storage.write_node_def(loc, node)

    result = WalkResult([], [])
    if unfinished_results(result, storage, parent, node, graph):
        return result

    if not storage.is_node_started(loc):
        return WalkResult([node_run_data], [])

    match node.type:
        case "eval":
            message = storage.read_output(parent.N(node.graph[0]), node.graph[1])
            g = GraphData(**json.loads(message))
            return walk_node(storage, loc, g.output_idx(), g)

        case "output":
            return WalkResult([node_run_data], [])

        case "const":
            return WalkResult([node_run_data], [])

        case "loop":
            return walk_loop(storage, parent, idx, node)

        case "map":
            return walk_map(storage, parent, idx, node)

        case "ifelse":
            pred = storage.read_output(parent.N(node.pred[0]), node.pred[1])
            next_node = node.if_true if pred == b"true" else node.if_false
            next_loc = parent.N(next_node[0])
            if storage.is_node_finished(next_loc):
                storage.link_outputs(loc, Labels.VALUE, next_loc, next_node[1])
                storage.mark_node_finished(loc)
                return WalkResult([], [])
            else:
                return walk_node(storage, parent, next_node[0], graph)

        case "function":
            return WalkResult([], [loc])

        case "input":
            return WalkResult([], [])
        case _:
            assert_never(node)


def walk_loop(
    storage: ControllerStorage, parent: Loc, idx: NodeIndex, loop: Loop
) -> WalkResult:
    loc = parent.N(idx)
    if storage.is_node_finished(loc):
        return WalkResult([], [], [])

    i = 0
    while storage.is_node_started(loc.L(i + 1)):
        i += 1
    new_location = loc.L(i)

    message = storage.read_output(loc.N(-1), BODY_PORT)
    g = GraphData(**json.loads(message))
    loop_outputs = g.nodes[g.output_idx()].inputs

    if not storage.is_node_finished(new_location):
        return walk_node(storage, new_location, g.output_idx(), g)

    # Latest iteration is finished. Do we BREAK or CONTINUE?
    should_continue = json.loads(storage.read_output(new_location, loop.continue_port))
    if should_continue is False:
        for k in loop_outputs:
            storage.link_outputs(loc, k, new_location, k)
        storage.mark_node_finished(loc)
        return WalkResult([], [])

    # Include old inputs. The acc_port is the only one that can change.
    ins = {k: (-1, k) for k in loop.inputs.keys()}
    ins.update(loop_outputs)
    node_run_data = NodeRunData(
        loc.L(i + 1),
        Eval((-1, BODY_PORT), ins),
        list(loop_outputs.keys()),
    )
    return WalkResult([node_run_data], [])


def walk_map(
    storage: ControllerStorage, parent: Loc, idx: NodeIndex, map: Map
) -> WalkResult:
    loc = parent.N(idx)
    result = WalkResult([], [])
    if storage.is_node_finished(loc):
        return result

    map_eles = storage.read_output_ports(parent.N(map.input_idx))
    unfinished = [p for p in map_eles if not storage.is_node_finished(loc.M(p))]
    message = storage.read_output(loc.N(-1), BODY_PORT)
    g = GraphData(**json.loads(message))
    [result.extend(walk_node(storage, loc.M(p), g.output_idx(), g)) for p in unfinished]

    if len(unfinished) > 0:
        return result

    for j in map_eles:
        storage.link_outputs(loc, j, loc.M(j), map.out_port)

    storage.mark_node_finished(loc)
    return result
