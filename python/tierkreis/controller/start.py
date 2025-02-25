import subprocess
from logging import getLogger

from tierkreis.controller.models import NodeLocation, OutputLocation
from tierkreis.controller.storage.protocol import ControllerStorage
from tierkreis.core import Labels
from tierkreis.core.function import FunctionName
from tierkreis.core.tierkreis_graph import (
    BoxNode,
    ConstNode,
    FunctionNode,
    InputNode,
    MatchNode,
    OutputNode,
    PortID,
    TagNode,
    TierkreisNode,
)
from tierkreis.core.values import TierkreisValue, VariantValue
from tierkreis.exceptions import TierkreisError
from tierkreis.core.protos.tierkreis.v1alpha1.graph import Value, StructValue, MapValue

logger = getLogger(__name__)


def start(
    storage: ControllerStorage,
    node_location: NodeLocation,
    tk_node: TierkreisNode,
    inputs: dict[PortID, OutputLocation],
    output_list: list[PortID],
) -> None:
    logger.debug(f"start {node_location} {tk_node} {inputs} {output_list}")
    if isinstance(tk_node, FunctionNode):
        name = tk_node.function_name.name
        start_function_node(storage, node_location, name, inputs, output_list)

    elif isinstance(tk_node, InputNode):
        storage.mark_node_finished(node_location)

    elif isinstance(tk_node, OutputNode):
        storage.mark_node_finished(node_location)

        parent_loc = NodeLocation(location=node_location.location[:-1])
        pipe_inputs_to_output_location(storage, parent_loc, inputs)
        storage.mark_node_finished(parent_loc)

    elif isinstance(tk_node, ConstNode):
        storage.write_output(node_location, Labels.VALUE, tk_node.value.to_proto())
        storage.mark_node_finished(node_location)

    elif isinstance(tk_node, TagNode):
        loc, port = inputs[Labels.VALUE]
        storage.write_output(
            node_location,
            Labels.VALUE,
            Value(
                struct=StructValue(
                    map={
                        "tag": Value(str=str(tk_node.tag_name)),
                        "node_location": Value(str=str(loc)),
                        "port": Value(str=str(port)),
                    }
                )
            ),
        )
        storage.mark_node_finished(node_location)

    elif isinstance(tk_node, BoxNode):
        raise NotImplementedError("box node")

    elif isinstance(tk_node, MatchNode):
        variant = VariantValue.from_proto(
            storage.read_output(*inputs[Labels.VARIANT_VALUE]).variant
        )
        assert isinstance(variant, VariantValue)
        storage.link_outputs(node_location, Labels.THUNK, *inputs[variant.tag])
        storage.mark_node_finished(node_location)

    else:
        raise TierkreisError(f"Unknown node type {tk_node}.")


def start_function_node(
    storage: ControllerStorage,
    node_location: NodeLocation,
    name: str,
    inputs: dict[PortID, OutputLocation],
    output_list: list[PortID],
):
    def_path = storage.write_node_definition(node_location, name, inputs, output_list)

    if name == "eval":
        pipe_inputs_to_output_location(storage, node_location.append_node(0), inputs)

    elif name == "loop":
        eval_inputs = {k: v for k, v in inputs.items()}
        eval_inputs["thunk"] = inputs["body"]
        start(
            storage,
            node_location.append_loop(0),
            FunctionNode(FunctionName("eval")),
            eval_inputs,
            output_list,
        )

    elif name == "map":
        raise NotImplementedError("MAP not implemented.")

    elif name == "copy":
        input_loc, input_port = list(inputs.values())[0]
        for output in output_list:
            storage.link_outputs(node_location, output, input_loc, input_port)
        storage.mark_node_finished(node_location)

    elif name == "switch":
        pred = storage.read_output(*inputs["pred"]).boolean
        if pred:
            storage.link_outputs(node_location, Labels.VALUE, *inputs["if_true"])
        else:
            storage.link_outputs(node_location, Labels.VALUE, *inputs["if_false"])
        storage.mark_node_finished(node_location)

    elif name == "discard":
        storage.mark_node_finished(node_location)

    elif name == name:
        logger.debug(f"Executing {(str(node_location), name, inputs, output_list)}")
        subprocess.run(["uv", "run", "python", "numerical-worker/main.py", def_path])


def pipe_inputs_to_output_location(
    storage: ControllerStorage,
    output_loc: NodeLocation,
    inputs: dict[PortID, OutputLocation],
) -> None:
    for new_port, (old_loc, old_port) in inputs.items():
        storage.link_outputs(output_loc, new_port, old_loc, old_port)
