import json
from logging import getLogger

from pydantic import BaseModel
from typing_extensions import assert_never

from tierkreis.controller.data.graph import Eval, Jsonable, NodeRunData
from tierkreis.controller.data.location import Loc, OutputLoc
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
    inputs = node.inputs
    output_list = node_run_data.output_list
    storage.write_worker_call_args(node_location, node.type, inputs, output_list)
    storage.write_node_def(node_location, node)

    logger.debug(f"start {node_location} {node} {inputs} {output_list}")
    if node.type == "function":
        name = node.function_name
        launcher_name = ".".join(name.split(".")[:-1])
        name = name.split(".")[-1]
        def_path = storage.write_worker_call_args(
            node_location, name, inputs, output_list
        )

        logger.debug(f"Executing {(str(node_location), name, inputs, output_list)}")
        executor.run(launcher_name, def_path)

    elif node.type == "input":
        storage.mark_node_finished(node_location)

    elif node.type == "output":
        storage.mark_node_finished(node_location)

        parent_loc = node_location.parent()
        if parent_loc is None:
            raise TierkreisError("Output node must have parent Loc.")

        pipe_inputs_to_output_location(storage, parent_loc, inputs)
        storage.mark_node_finished(parent_loc)

    elif node.type == "const":
        bs = bytes_from_value(node.value)
        storage.write_output(node_location, Labels.VALUE, bs)
        storage.mark_node_finished(node_location)

    elif node.type == "eval":
        pass

    elif node.type == "loop":
        start(
            storage,
            executor,
            NodeRunData(node_location.L(0), Eval(node.body, inputs), output_list),
        )

    elif node.type == "map":
        parent = node_location.parent()
        if parent is None:
            raise TierkreisError("MAP node must have parent.")

        input_values = storage.read_output_ports(parent + node.input_idx)
        input_indices = [int(s) for s in input_values]
        input_indices.sort()
        for i in input_indices:
            inputs[node.input_port] = (parent + node.input_idx, str(i))
            start(
                storage,
                executor,
                NodeRunData(node_location.M(i), Eval(node.body, inputs), output_list),
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


def bytes_from_value(value: Jsonable) -> bytes:
    if isinstance(value, BaseModel):
        return value.model_dump_json().encode()

    return json.dumps(value).encode()
