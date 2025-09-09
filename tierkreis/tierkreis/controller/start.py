from dataclasses import dataclass
import logging
import subprocess
import sys

from tierkreis.controller.data.core import PortID
from tierkreis.controller.data.types import bytes_from_ptype, ptype_from_bytes
from tierkreis.controller.executor.in_memory_executor import InMemoryExecutor
from tierkreis.controller.storage.adjacency import outputs_iter
from tierkreis.paths import Paths
from tierkreis.runner.commands import HandleError
from typing_extensions import assert_never

from tierkreis.consts import PACKAGE_PATH
from tierkreis.controller.data.graph import Eval, GraphData, NodeDef
from tierkreis.controller.data.location import Loc, OutputLoc
from tierkreis.controller.executor.protocol import ControllerExecutor
from tierkreis.controller.storage.protocol import ControllerStorage
from tierkreis.controller.storage.in_memory import ControllerInMemoryStorage
from tierkreis.labels import Labels
from tierkreis.exceptions import TierkreisError

logger = logging.getLogger(__name__)


@dataclass
class NodeRunData:
    node_location: Loc
    node: NodeDef
    output_list: list[PortID]


def start_nodes(
    storage: ControllerStorage,
    executor: ControllerExecutor,
    node_run_data: list[NodeRunData],
) -> None:
    started_locs: set[Loc] = set()
    for node_run_datum in node_run_data:
        if node_run_datum.node_location in started_locs:
            continue
        start(storage, executor, node_run_datum)
        started_locs.add(node_run_datum.node_location)


def run_command(cmd: str, loc: Loc, paths: Paths) -> None:
    cmd = HandleError(str(paths.error_path(loc)))(cmd)

    with open(paths.logs_path(), "a") as lfh:
        with open(paths.error_logs_path(loc), "a") as efh:
            proc = subprocess.Popen(
                ["bash"],
                start_new_session=True,
                stdin=subprocess.PIPE,
                stderr=efh,
                stdout=lfh,
            )
            proc.communicate(f"{cmd} ".encode(), timeout=10)
            proc.communicate(None, timeout=10)


def start(
    storage: ControllerStorage, executor: ControllerExecutor, node_run_data: NodeRunData
) -> None:
    loc = node_run_data.node_location
    node = node_run_data.node
    output_list = node_run_data.output_list

    storage.write_node_def(loc, node)

    parent = loc.parent()
    if parent is None:
        raise TierkreisError(f"{node.type} node must have parent Loc.")

    ins = {k: (parent.N(idx), p) for k, (idx, p) in node.inputs.items()}

    logger.debug(f"start {loc} {node} {ins} {output_list}")
    if node.type == "function":
        name = node.function_name
        launcher_name = ".".join(name.split(".")[:-1])
        name = name.split(".")[-1]
        args_path = storage.write_worker_call_args(loc, name, ins, output_list)
        logger.debug(f"Executing {(str(loc), name, ins, output_list)}")

        is_in_memory = isinstance(storage, ControllerInMemoryStorage) and isinstance(
            executor, InMemoryExecutor
        )
        if is_in_memory:
            # In-memory executor is an exception: it runs the command itself.
            executor.command(launcher_name, storage.paths.workflow_id, loc)
        elif launcher_name == "builtins":
            run_command(
                f"{sys.executable} {PACKAGE_PATH}/tierkreis/builtins/main.py {args_path}",
                loc,
                storage.paths,
            )
        else:
            cmd = executor.command(launcher_name, storage.paths.workflow_id, loc)
            run_command(cmd, loc, storage.paths)

    elif node.type == "input":
        input_loc = parent.N(-1)
        storage.link_outputs(loc, node.name, input_loc, node.name)
        storage.mark_node_finished(loc)

    elif node.type == "output":
        storage.mark_node_finished(loc)

        pipe_inputs_to_output_location(storage, parent, ins)
        storage.mark_node_finished(parent)

    elif node.type == "const":
        bs = bytes_from_ptype(node.value)
        storage.write_output(loc, Labels.VALUE, bs)
        storage.mark_node_finished(loc)

    elif node.type == "eval":
        message = storage.read_output(parent.N(node.graph[0]), node.graph[1])
        g = ptype_from_bytes(message, GraphData)

        if g.remaining_inputs(set(ins.keys())):
            g.fixed_inputs.update(ins)
            storage.write_output(loc, "body", g.model_dump_json().encode())
            storage.mark_node_finished(loc)
            return

        ins["body"] = (parent.N(node.graph[0]), node.graph[1])
        ins.update(g.fixed_inputs)

        pipe_inputs_to_output_location(storage, loc.N(-1), ins)

    elif node.type == "loop":
        ins["body"] = (parent.N(node.body[0]), node.body[1])
        pipe_inputs_to_output_location(storage, loc.N(-1), ins)
        start(
            storage,
            executor,
            NodeRunData(
                loc.L(0),
                Eval((-1, "body"), {k: (-1, k) for k, _ in ins.items()}, node.outputs),
                output_list,
            ),
        )

    elif node.type == "map":
        first_ref = next(x for x in ins.values() if x[1] == "*")
        map_eles = outputs_iter(storage, first_ref[0])
        for idx, p in map_eles:
            eval_inputs: dict[PortID, tuple[Loc, PortID]] = {}
            eval_inputs["body"] = (parent.N(node.body[0]), node.body[1])
            for k, (i, port) in ins.items():
                if port == "*":
                    eval_inputs[k] = (i, p)
                else:
                    eval_inputs[k] = (i, port)
            pipe_inputs_to_output_location(storage, loc.M(idx).N(-1), eval_inputs)
            # Necessary in the node visualization
            storage.write_node_def(
                loc.M(idx), Eval((-1, "body"), node.inputs, node.outputs)
            )

    elif node.type == "ifelse":
        pass

    elif node.type == "eifelse":
        pass
    else:
        assert_never(node)


def pipe_inputs_to_output_location(
    storage: ControllerStorage,
    output_loc: Loc,
    inputs: dict[PortID, OutputLoc],
) -> None:
    for new_port, (old_loc, old_port) in inputs.items():
        storage.link_outputs(output_loc, new_port, old_loc, old_port)
