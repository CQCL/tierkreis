import json
from dataclasses import dataclass
from logging import getLogger
from typing import assert_never

from tierkreis.controller.data.graph import Eval, GraphData, NodeRunData
from tierkreis.controller.data.location import Loc
from tierkreis.controller.storage.protocol import ControllerStorage
from tierkreis.core import Labels

logger = getLogger(__name__)


@dataclass
class WalkResult:
    inputs_ready: list[NodeRunData]
    started: list[Loc]

    def extend(self, walk_result: "WalkResult") -> None:
        self.inputs_ready.extend(walk_result.inputs_ready)
        self.started.extend(walk_result.started)


def walk_node(storage: ControllerStorage, node_location: Loc) -> WalkResult:
    """Should only be called when a node has started and has not finished."""

    logger.debug(f"\n\nRESUME {node_location}")
    node = storage.read_node_def(node_location)

    match node.type:
        case "eval":
            return walk_eval(storage, node_location)

        case "loop":
            return walk_loop(storage, node_location)

        case "map":
            return walk_map(storage, node_location)

        case "const" | "function" | "input" | "output":
            logger.debug(f"{node_location} ({node.type}) already started")
            return WalkResult([], [node_location])

        case _:
            assert_never(node)


def walk_eval(storage: ControllerStorage, node_location: Loc) -> WalkResult:
    logger.debug("walk_eval")
    walk_result = WalkResult([], [])
    message = storage.read_output(node_location.N(-1), Labels.THUNK)
    graph = GraphData(**json.loads(message))

    logger.debug(len(graph.nodes))
    for i, node in graph.nodes.items():
        new_location = node_location + i
        logger.debug(f"new_location: {new_location}")

        if storage.is_node_finished(new_location):
            logger.debug(f"{new_location} is finished")
            continue

        if storage.is_node_started(new_location):
            logger.debug(f"{new_location} is started")
            walk_result.extend(walk_node(storage, new_location))
            continue

        if all(
            storage.is_node_finished(node_location + i)
            for (i, _) in node.inputs.values()
        ):
            logger.debug(f"{new_location} is_ready_to_start")
            outputs = graph.outputs[i]
            node.inputs = {
                k: (node_location + i, p) for k, (i, p) in node.inputs.items()
            }
            node_run_data = NodeRunData(new_location, node, list(outputs))
            walk_result.inputs_ready.append(node_run_data)
            continue

        logger.debug(f"node not ready to start {new_location}")

    return walk_result


def walk_loop(storage: ControllerStorage, node_location: Loc) -> WalkResult:
    i = 0
    while storage.is_node_started(node_location.L(i + 1)):
        i += 1
    new_location = node_location.L(i)
    logger.debug(f"found latest iteration of loop: {new_location}")

    if not storage.is_node_finished(new_location):
        return walk_node(storage, new_location)

    # Latest iteration is finished. Do we BREAK or CONTINUE?
    should_continue = json.loads(storage.read_output(new_location, "should_continue"))
    if should_continue is False:
        storage.link_outputs(node_location, Labels.VALUE, new_location, Labels.VALUE)
        storage.mark_node_finished(node_location)
        return WalkResult([], [])

    # Include old inputs. The .value is the only one that can change.
    input_paths = storage.read_worker_call_args(node_location).inputs
    inputs = {k: (new_location.N(-1), v.name) for k, v in input_paths.items()}
    inputs[Labels.VALUE] = (new_location, Labels.VALUE)
    inputs[Labels.THUNK] = (new_location.N(-1), Labels.THUNK)

    node_run_data = NodeRunData(
        node_location.L(i + 1),
        Eval(inputs[Labels.THUNK], inputs),
        [Labels.VALUE],
    )
    return WalkResult([node_run_data], [])


def walk_map(storage: ControllerStorage, node_location: Loc) -> WalkResult:
    walk_result = WalkResult([], [])
    N = 0
    all_finished = True
    while storage.is_node_started(node_location.M(N + 1)):
        N += 1

    for i in range(N + 1):
        loc = node_location.M(i)
        if not storage.is_node_finished(loc):
            all_finished = False
            walk_result.extend(walk_node(storage, loc))

    if all_finished is True:
        for j in range(N + 1):
            loc = node_location.M(j)
            storage.link_outputs(
                node_location, str(j), loc, Labels.VALUE
            )  # TODO: graphbuilder has to know we use VALUE
            storage.mark_node_finished(node_location)

    return walk_result
