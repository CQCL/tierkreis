import json
from logging import getLogger

from pydantic import BaseModel
from typing_extensions import assert_never

from tierkreis.controller.data.graph import Eval
from tierkreis.controller.data.location import Loc, NodeRunData, OutputLoc
from tierkreis.controller.executor.protocol import ControllerExecutor
from tierkreis.controller.storage.protocol import ControllerStorage
from tierkreis.core import Labels
from tierkreis.core.tierkreis_graph import PortID
from tierkreis.exceptions import TierkreisError

logger = getLogger(__name__)


def start_nodes(
    storage: ControllerStorage,
    executor: ControllerExecutor,
    node_run_data: list[NodeRunData],
) -> None:
    for node_run_datum in node_run_data:
        start(storage, executor, node_run_datum)


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
        input_values = storage.read_output_ports(parent.N(node.input_idx))
        input_indices = [int(s) for s in input_values]

        ins["body"] = (parent.N(node.body[0]), node.body[1])
        pipe_inputs_to_output_location(storage, node_location.N(-1), ins)

        for i in input_indices:
            storage.link_outputs(
                node_location.N(-1), str(i), parent.N(node.input_idx), str(i)
            )
            eval_inputs = {k: (-1, k) for k in ins.keys()}
            eval_inputs[node.in_port] = (-1, str(i))
            start(
                storage,
                executor,
                NodeRunData(
                    node_location.M(i), Eval((-1, "body"), eval_inputs), output_list
                ),
            )

    else:
        assert_never(node)


def pipe_inputs_to_output_location(
    storage: ControllerStorage,
    output_loc: Loc,
    inputs: dict[PortID, OutputLoc],
) -> None:
    for new_port, (old_loc, old_port) in inputs.items():
        storage.link_outputs(output_loc, new_port, old_loc, old_port)
