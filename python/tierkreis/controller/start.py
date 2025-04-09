import json
from logging import getLogger

from pydantic import BaseModel

from tierkreis.controller.data.graph_data import Eval, Jsonable
from tierkreis.controller.executor.protocol import ControllerExecutor
from tierkreis.controller.models import NodeLocation, NodeRunData, OutputLocation
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
    inputs = node_run_data.inputs
    output_list = node_run_data.output_list
    storage.write_node_definition(node_location, node.type, inputs, output_list)

    logger.debug(f"start {node_location} {node} {inputs} {output_list}")
    if node.type == "function":
        name = node.function_name
        start_function_node(storage, executor, node_location, name, inputs, output_list)

    elif node.type == "input":
        storage.write_node_definition(node_location, "input", inputs, output_list)
        storage.mark_node_finished(node_location)

    elif node.type == "output":
        storage.write_node_definition(node_location, "output", inputs, output_list)
        storage.mark_node_finished(node_location)

        parent_loc = NodeLocation(location=node_location.location[:-1])
        pipe_inputs_to_output_location(storage, parent_loc, inputs)
        storage.mark_node_finished(parent_loc)

    elif node.type == "const":
        storage.write_node_definition(node_location, "const", inputs, output_list)
        bs = bytes_from_value(node.value)
        storage.write_output(node_location, Labels.VALUE, bs)
        storage.mark_node_finished(node_location)

    elif node.type == "eval":
        pipe_inputs_to_output_location(storage, node_location.append_node(0), inputs)

    elif node.type == "loop":
        eval_inputs = {k: v for k, v in inputs.items()}
        eval_inputs["thunk"] = inputs["body"]
        start(
            storage,
            executor,
            NodeRunData(
                node_location.append_loop(0),
                Eval((0, Labels.THUNK), {}, []),  # TODO: put inputs in Eval
                eval_inputs,
                output_list,
            ),
        )

    elif node.type == "map":
        raise NotImplementedError("MAP not implemented.")

    else:
        raise TierkreisError(f"Unknown node type {node}.")


def start_function_node(
    storage: ControllerStorage,
    executor: ControllerExecutor,
    node_location: NodeLocation,
    name: str,
    inputs: dict[PortID, OutputLocation],
    output_list: list[PortID],
):
    launcher_name = ".".join(name.split(".")[:-1])
    name = name.split(".")[-1]
    def_path = storage.write_node_definition(node_location, name, inputs, output_list)

    # if name == "copy":
    #     input_loc, input_port = list(inputs.values())[0]
    #     for output in output_list:
    #         storage.link_outputs(node_location, output, input_loc, input_port)
    #     storage.mark_node_finished(node_location)

    if name == "switch":
        pred = json.loads(storage.read_output(*inputs["pred"]))
        if pred:
            storage.link_outputs(node_location, Labels.VALUE, *inputs["if_true"])
        else:
            storage.link_outputs(node_location, Labels.VALUE, *inputs["if_false"])
        storage.mark_node_finished(node_location)

    elif name == "discard":
        storage.mark_node_finished(node_location)

    else:
        logger.debug(f"Executing {(str(node_location), name, inputs, output_list)}")
        executor.run(launcher_name, def_path)


def pipe_inputs_to_output_location(
    storage: ControllerStorage,
    output_loc: NodeLocation,
    inputs: dict[PortID, OutputLocation],
) -> None:
    for new_port, (old_loc, old_port) in inputs.items():
        storage.link_outputs(output_loc, new_port, old_loc, old_port)


def bytes_from_value(value: Jsonable) -> bytes:
    if isinstance(value, BaseModel):
        return value.model_dump_json().encode()

    return json.dumps(value).encode()
