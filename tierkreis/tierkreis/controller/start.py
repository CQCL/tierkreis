import json
from logging import getLogger
import logging
from pathlib import Path
import subprocess
import sys

from pydantic import BaseModel
from typing_extensions import assert_never

from tierkreis.controller.consts import PACKAGE_PATH
from tierkreis.controller.data.graph import Eval, PortID
from tierkreis.controller.data.location import Loc, NodeRunData, OutputLoc
from tierkreis.controller.executor.protocol import ControllerExecutor
from tierkreis.controller.storage.protocol import ControllerStorage
from tierkreis.labels import Labels
from tierkreis.exceptions import TierkreisError

logger = logging.getLogger(__name__)


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


def run_builtin(def_path: Path, logs_path: Path) -> None:
    formatter = logging.Formatter(
        fmt="%(asctime)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    handler = logging.FileHandler(logs_path, mode="a")
    handler.setFormatter(formatter)
    logger = getLogger("builtins")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)

    logger.info("START builtin %s", def_path)
    with open(logs_path, "a") as fh:
        subprocess.Popen(
            [sys.executable, "main.py", def_path],
            start_new_session=True,
            cwd=PACKAGE_PATH / "builtins",
            stderr=fh,
            stdout=fh,
        )


def start(
    storage: ControllerStorage, executor: ControllerExecutor, node_run_data: NodeRunData
) -> None:
    node_location = node_run_data.node_location
    node = node_run_data.node
    output_list = node_run_data.output_list

    storage.write_node_def(node_location, node)

    parent = node_location.parent()
    if parent is None:
        raise TierkreisError(f"{node.type} node must have parent Loc.")

    ins = {k: (parent.N(idx), p) for k, (idx, p) in node.inputs.items()}
    storage.write_worker_call_args(node_location, node.type, ins, output_list)

    logger.debug(f"start {node_location} {node} {ins} {output_list}")
    if node.type == "function":
        name = node.function_name
        launcher_name = ".".join(name.split(".")[:-1])
        name = name.split(".")[-1]
        def_path = storage.write_worker_call_args(node_location, name, ins, output_list)
        logger.debug(f"Executing {(str(node_location), name, ins, output_list)}")

        if launcher_name == "builtins":
            run_builtin(def_path, storage.logs_path)
        else:
            executor.run(launcher_name, def_path)

    elif node.type == "input":
        input_loc = parent.N(-1)
        storage.link_outputs(node_location, node.name, input_loc, node.name)
        storage.mark_node_finished(node_location)

    elif node.type == "output":
        storage.mark_node_finished(node_location)

        pipe_inputs_to_output_location(storage, parent, ins)
        storage.mark_node_finished(parent)

    elif node.type == "const":
        bs = (
            node.value.model_dump_json().encode()
            if isinstance(node.value, BaseModel)
            else json.dumps(node.value).encode()
        )
        storage.write_output(node_location, Labels.VALUE, bs)
        storage.mark_node_finished(node_location)

    elif node.type == "eval":
        ins["body"] = (parent.N(node.graph[0]), node.graph[1])
        pipe_inputs_to_output_location(storage, node_location.N(-1), ins)

    elif node.type == "loop":
        ins["body"] = (parent.N(node.body[0]), node.body[1])
        pipe_inputs_to_output_location(storage, node_location.N(-1), ins)
        start(
            storage,
            executor,
            NodeRunData(
                node_location.L(0),
                Eval((-1, "body"), {k: (-1, k) for k, _ in ins.items()}),
                output_list,
            ),
        )

    elif node.type == "map":
        ins["body"] = (parent.N(node.body[0]), node.body[1])
        pipe_inputs_to_output_location(storage, node_location.N(-1), ins)

        map_eles = storage.read_output_ports(parent.N(node.input_idx))
        for p in map_eles:
            storage.link_outputs(node_location.N(-1), p, parent.N(node.input_idx), p)
            eval_inputs = {k: (-1, k) for k in ins.keys()}
            eval_inputs[node.in_port] = (-1, p)
            start(
                storage,
                executor,
                NodeRunData(
                    node_location.M(p), Eval((-1, "body"), eval_inputs), output_list
                ),
            )

    elif node.type == "ifelse":
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
