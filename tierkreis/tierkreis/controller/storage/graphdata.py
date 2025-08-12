from pathlib import Path
from uuid import UUID
from typing import Any


from tierkreis.controller.data.core import NodeIndex, PortID
from tierkreis.controller.data.graph import (
    Eval,
    GraphData,
    NodeDef,
    graph_node_from_loc,
)
from tierkreis.controller.data.location import (
    Loc,
    OutputLoc,
    WorkerCallArgs,
    get_last_index,
)
from tierkreis.exceptions import TierkreisError
from tierkreis.controller.storage.in_memory import NodeData


class GraphDataStorage:
    def __init__(
        self,
        workflow_id: UUID,
        graph: GraphData,
        name: str | None = None,
    ) -> None:
        self.workflow_id = workflow_id
        self.name = name
        self.nodes: dict[Loc, NodeData] = {}
        self.graph = graph
        self.logs_path = Path("")

    def write_node_def(self, node_location: Loc, node: NodeDef) -> None:
        raise NotImplementedError("GraphDataStorage is read only storage.")

    def read_node_def(self, node_location: Loc) -> NodeDef:
        if (last := node_location.pop_last()) is None:
            return Eval((-1, "body"), {})
        if last[0][0] in ["M", "L"]:
            return Eval((-1, "body"), {})
        node, graph = graph_node_from_loc(node_location, self.graph)
        return node

    def write_worker_call_args(
        self,
        node_location: Loc,
        function_name: str,
        inputs: dict[PortID, OutputLoc],
        output_list: list[PortID],
    ) -> Path:
        raise NotImplementedError("GraphDataStorage is read only storage.")

    def read_worker_call_args(self, node_location: Loc) -> WorkerCallArgs:
        raise TierkreisError(
            f"Node location {node_location} doesn't have a associate call args."
        )

    def read_errors(self, node_location: Loc) -> str:
        return ""

    def node_has_error(self, node_location: Loc) -> bool:
        return False

    def write_node_errors(self, node_location: Loc, error_logs: str) -> None:
        raise NotImplementedError("GraphDataStorage is read only storage.")

    def mark_node_finished(self, node_location: Loc) -> None:
        raise NotImplementedError("GraphDataStorage is read only storage.")

    def is_node_finished(self, node_location: Loc) -> bool:
        return False

    def link_outputs(
        self,
        new_location: Loc,
        new_port: PortID,
        old_location: Loc,
        old_port: PortID,
    ) -> None:
        raise NotImplementedError("GraphDataStorage is read only storage.")

    def write_output(
        self, node_location: Loc, output_name: PortID, value: bytes
    ) -> Path:
        raise NotImplementedError("GraphDataStorage is read only storage.")

    def read_output(self, node_location: Loc, output_name: PortID) -> bytes:
        parent_loc = node_location.parent()
        if parent_loc is None:
            raise TierkreisError("Node needs parent loc!")
        _, graph = graph_node_from_loc(parent_loc, self.graph)
        if -1 == get_last_index(node_location) and output_name == "body":
            return graph.model_dump_json().encode()
        if (last := node_location.pop_last()) is None:
            outputs = _build_outputs(graph)
        elif last[0][0] in ["M", "L"]:
            outputs = _build_outputs(graph)
        else:
            outputs = _build_outputs(graph, get_last_index(node_location))
        if output_name in outputs:
            if output := outputs[output_name]:
                return output
            return b"null"
        raise TierkreisError(f"No output named {output_name} in node {node_location}")

    def read_output_ports(self, node_location: Loc) -> list[PortID]:
        parent_loc = node_location.parent()
        if parent_loc is None:
            raise TierkreisError("Node needs parent loc!")
        _, graph = graph_node_from_loc(parent_loc, self.graph)
        if (last := node_location.pop_last()) is None:
            outputs = _build_outputs(graph)
        elif last[0][0] in ["M", "L"]:
            outputs = _build_outputs(graph)
        elif get_last_index(node_location) == -1:
            outputs = {"body": None}
        else:
            outputs = _build_outputs(graph, get_last_index(node_location))
        return list(filter(lambda k: k != "*", outputs.keys()))

    def is_node_started(self, node_location: Loc) -> bool:
        return False

    def read_metadata(self, node_location: Loc) -> dict[str, Any]:
        return self.nodes[node_location].metadata

    def write_metadata(self, node_location: Loc) -> None:
        raise NotImplementedError("GraphDataStorage is read only storage.")


def _build_outputs(
    graph: GraphData, index: int | NodeIndex | None = None
) -> dict[PortID, None | bytes]:
    """Safely read the outputs, works for graphs without output nodes."""
    if index is None:
        index = graph.output_idx()
    try:
        outputs: dict[PortID, None | bytes] = {
            output: None for output in graph.node_outputs[index]
        }
    except TierkreisError:
        # partial graph without an output
        outputs = {}
    if "*" in outputs:
        outputs["0"] = None
    return outputs
