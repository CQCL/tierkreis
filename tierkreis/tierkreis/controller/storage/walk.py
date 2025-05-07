import json
from dataclasses import dataclass, field
from logging import getLogger
from typing import assert_never

from tierkreis.controller.consts import BODY_PORT
from tierkreis.controller.data.graph import Eval, GraphData, Loop, Map
from tierkreis.controller.data.location import Loc, NodeRunData
from tierkreis.controller.storage.adjacency import in_edges
from tierkreis.controller.storage.protocol import ControllerStorage
from tierkreis.exceptions import TierkreisError

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


def walk_node(storage: ControllerStorage, loc: Loc) -> WalkResult:
    """Should only be called when a node has started and has not finished."""

    logger.debug(f"\n\nRESUME {loc}")
    if storage.node_has_error(loc):
        logger.error(f"Node {loc} has encountered an error:")
        logger.error(f"\n\n{storage.read_errors(loc)}\n\n")
        return WalkResult([], [], [loc])
    node = storage.read_node_def(loc)

    match node.type:
        case "eval":
            return walk_eval(storage, loc)

        case "loop":
            return walk_loop(storage, loc, node)

        case "map":
            return walk_map(storage, loc, node)

        case "const" | "function" | "input" | "output":
            logger.debug(f"{loc} ({node.type}) already started")
            return WalkResult([], [loc])

        case _:
            assert_never(node)


def walk_eval(storage: ControllerStorage, loc: Loc) -> WalkResult:
    logger.debug("walk_eval")
    walk_result = WalkResult([], [])
    message = storage.read_output(loc.N(-1), BODY_PORT)
    graph = GraphData(**json.loads(message))

    logger.debug(len(graph.nodes))
    for i, node in enumerate(graph.nodes):
        new_location = loc.N(i)
        logger.debug(f"new_location: {new_location}")

        if storage.is_node_finished(new_location):
            logger.debug(f"{new_location} is finished")
            continue

        if storage.is_node_started(new_location):
            logger.debug(f"{new_location} is started")
            walk_result.extend(walk_node(storage, new_location))
            continue

        parents = in_edges(node)
        if all(storage.is_node_finished(loc.N(i)) for (i, _) in parents.values()):
            logger.debug(f"{new_location} is_ready_to_start")
            outputs = graph.outputs[i]
            node_run_data = NodeRunData(new_location, node, list(outputs))
            walk_result.inputs_ready.append(node_run_data)
            continue

        logger.debug(f"node not ready to start {new_location}")

    return walk_result


def walk_loop(storage: ControllerStorage, loc: Loc, loop: Loop) -> WalkResult:
    acc_port = loop.acc_port
    i = 0
    while storage.is_node_started(loc.L(i + 1)):
        i += 1
    new_location = loc.L(i)
    logger.debug(f"found latest iteration of loop: {new_location}")

    if not storage.is_node_finished(new_location):
        return walk_node(storage, new_location)

    # Latest iteration is finished. Do we BREAK or CONTINUE?
    should_continue = json.loads(storage.read_output(new_location, loop.continue_port))
    if should_continue is False:
        storage.link_outputs(loc, acc_port, new_location, acc_port)
        storage.mark_node_finished(loc)
        return WalkResult([], [])

    # Include old inputs. The .acc_port is the only one that can change.
    ins = {k: (-1, k) for k in loop.inputs.keys() if k != acc_port}
    storage.link_outputs(loc.L(i + 1).N(-1), acc_port, new_location, acc_port)
    node_run_data = NodeRunData(loc.L(i + 1), Eval((-1, "body"), ins), [acc_port])
    return WalkResult([node_run_data], [])


def walk_map(storage: ControllerStorage, loc: Loc, map: Map) -> WalkResult:
    walk_result = WalkResult([], [])
    parent = loc.parent()
    if parent is None:
        raise TierkreisError("MAP node must have parent.")

    map_eles = storage.read_output_ports(parent.N(map.input_idx))
    unfinished = [p for p in map_eles if not storage.is_node_finished(loc.M(p))]
    [walk_result.extend(walk_node(storage, loc.M(p))) for p in unfinished]

    if len(unfinished) > 0:
        return walk_result

    for j in map_eles:
        storage.link_outputs(loc, j, loc.M(j), map.out_port)
        storage.mark_node_finished(loc)

    return walk_result
