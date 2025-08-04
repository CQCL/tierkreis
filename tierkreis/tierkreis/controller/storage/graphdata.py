from pathlib import Path
from uuid import UUID
from typing import Any, assert_never
from datetime import datetime


from tierkreis.controller.data.core import PortID
from tierkreis.controller.data.graph import Const, Eval, GraphData, NodeDef
from tierkreis.controller.data.location import (
    Loc,
    OutputLoc,
    WorkerCallArgs,
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
        self._initialize_storage(graph)
        self.logs_path = Path("")

    def write_node_def(self, node_location: Loc, node: NodeDef) -> None:
        raise NotImplementedError("GraphDataStorage is read only storage.")

    def read_node_def(self, node_location: Loc) -> NodeDef:
        node = self._node_from_loc(node_location, self.graph)
        if result := node.definition:
            return result
        raise TierkreisError(f"Node definition of {node_location} not found.")

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
        node = self._node_from_loc(node_location, self.graph)
        if output_name in node.outputs:
            if output := node.outputs[output_name]:
                return output
            return b"null"
        raise TierkreisError(f"No output named {output_name} in node {node_location}")

    def read_output_ports(self, node_location: Loc) -> list[PortID]:
        node = self._node_from_loc(node_location, self.graph)
        return list(filter(lambda k: k != "*", node.outputs.keys()))

    def is_node_started(self, node_location: Loc) -> bool:
        return False

    def read_metadata(self, node_location: Loc) -> dict[str, Any]:
        return self.nodes[node_location].metadata

    def write_metadata(self, node_location: Loc) -> None:
        raise NotImplementedError("GraphDataStorage is read only storage.")

    def _initialize_storage(self, graph: GraphData) -> None:
        """Evaluate a graph symbolically, creating nodes in the storage.

        :param graph: The graph to evaluate symbolically.
        :type graph: GraphData
        """
        outputs = _build_outputs(graph)
        parent_loc = Loc()
        self.nodes[parent_loc] = NodeData(
            definition=Eval((-1, "body"), {}),
            outputs=outputs,
        )
        self.nodes[parent_loc].metadata["start_time"] = datetime.now().isoformat()

        self.nodes[parent_loc.N(-1)] = NodeData(
            outputs={"body": graph.model_dump_json().encode()},
        )

    def _node_from_loc(
        self,
        node_location: Loc,
        graph: GraphData,
    ) -> NodeData:
        # "read-only"-> if we seen it once it won't change
        if node_location in self.nodes:
            return self.nodes[node_location]
        # start with the full graph
        if len(graph.nodes) == 0:
            raise TierkreisError("Cannot convert location to node. Reason: Empty Graph")
        # We move through the recursion by changing node_loc -> .parent()
        parent_location = node_location.parent()
        if parent_location is None:
            raise TierkreisError(
                "Cannot convert location to node. Reason: Invalid Graph"
            )

        # Get the current node from the graph. Its at the end of the loc e.g -.N0.M1 <- M1 is relevant
        _, node_id = node_location.steps()[-1]
        if isinstance(node_id, str):
            # map nodes can have port names here
            if "-" in node_id:
                node_id = node_id.split("-")[1]
            if node_id == "*":
                node_id = "0"
            try:
                node_id = int(node_id)
            except ValueError:
                node_id = 0
        node = graph.nodes[node_id]

        # Build up the intermediate nodes recursively, nested graphs are wrapped in const nodes
        # For eval nodes we expect a Node at N-1 with a body output
        # For loop and map we expect an empty eval node at M0/L1
        # For loop and map we don't have values yet but now the internal graph
        # so we set up a dummy value 0
        match node.type:
            case "eval":
                graph = _unwrap_graph(graph.nodes[node.graph[0]], node.type)
                self.nodes[node_location.N(-1)] = NodeData(
                    outputs={"body": graph.model_dump_json().encode()},
                )
                self._node_from_loc(parent_location, graph)

            case "loop":
                graph = _unwrap_graph(graph.nodes[node.body[0]], node.type)
                outputs = _build_outputs(graph)
                self.nodes[node_location.L(0)] = NodeData(
                    definition=Eval((-1, "body"), {}), outputs=outputs
                )
                self.nodes[node_location.L(0).N(-1)] = NodeData(
                    outputs={"body": graph.model_dump_json().encode()},
                )
                self._node_from_loc(parent_location, graph)

            case "map":
                graph = _unwrap_graph(graph.nodes[node.body[0]], node.type)
                outputs = _build_outputs(graph)
                if "*" in outputs:
                    outputs["0"] = None
                self.nodes[node_location.M("0")] = NodeData(
                    definition=Eval((-1, "body"), {}),
                    outputs=outputs,
                )
                self.nodes[node_location.M("0").N(-1)] = NodeData(
                    outputs={"body": graph.model_dump_json().encode()},
                )
                self._node_from_loc(parent_location, graph)
            case "const" | "function" | "input" | "output" | "ifelse" | "eifelse":
                pass
            case _:
                assert_never(node)

        outputs: dict[PortID, bytes | None] = _build_outputs(graph)
        if "*" in outputs:
            outputs["0"] = None
        self.nodes[node_location] = NodeData(
            definition=node,
            outputs=outputs,
        )
        return self.nodes[node_location]


def _unwrap_graph(node: NodeDef, node_type: str) -> GraphData:
    """Safely unwraps a const nodes GraphData."""
    if not isinstance(node, Const):
        raise TierkreisError(
            f"Cannot convert location to node. Reason: {node_type} does not wrap const"
        )
    if not isinstance(node.value, GraphData):
        raise TierkreisError(
            "Cannot convert location to node. Reason: const value is not a graph"
        )
    return node.value


def _build_outputs(graph: GraphData) -> dict[PortID, None | bytes]:
    """Safely read the outputs, works for graphs without output nodes."""
    try:
        outputs: dict[PortID, None | bytes] = {
            output: None for output in graph.node_outputs[graph.output_idx()]
        }
    except TierkreisError:
        # partial graph without an output
        outputs = {}
    return outputs
