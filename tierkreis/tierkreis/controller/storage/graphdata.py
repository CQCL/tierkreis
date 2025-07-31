from collections import defaultdict
from pathlib import Path
from uuid import UUID
from typing import Any, assert_never
from datetime import datetime


from tierkreis.controller.data.core import PortID
from tierkreis.controller.data.graph import Eval, GraphData, NodeDef
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
        self.nodes: dict[Loc, NodeData] = defaultdict(lambda: NodeData())
        self.graph = graph
        self._initialize_storage(graph)
        self.logs_path = Path("")

    def write_node_def(self, node_location: Loc, node: NodeDef) -> None:
        raise NotImplementedError("GraphDataStorage is read only storage.")

    def read_node_def(self, node_location: Loc) -> NodeDef:
        node = self._node_from_loc(node_location)
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
        node = self._node_from_loc(node_location)
        if result := node.call_args:
            return result
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
        node = self._node_from_loc(node_location)
        if output_name in node.outputs:
            if output := node.outputs[output_name]:
                return output
            return b"null"
        raise TierkreisError(f"No output named {output_name} in node {node_location}")

    def read_output_ports(self, node_location: Loc) -> list[PortID]:
        node = self._node_from_loc(node_location)
        return list(filter(lambda k: k != "*", node.outputs.keys()))

    def is_node_started(self, node_location: Loc) -> bool:
        return False

    def read_metadata(self, node_location: Loc) -> dict[str, Any]:
        return self.nodes[node_location].metadata

    def write_metadata(self, node_location: Loc) -> None:
        raise NotImplementedError("GraphDataStorage is read only storage.")

    def _initialize_storage(self, graph: GraphData, parent_loc: Loc = Loc()) -> None:
        """Evaluate a graph symbolically, creating nodes in the storage.

        This is used internally to create the visualization of symbolic graphs.
        Recursively creates all nodes by parsing the graph structure.
        Assumes that nested graphs are wrapped in a Const parent node.
        Starts from the final output node.

        :param graph: The graph to evaluate symbolically.
        :type graph: GraphData
        :param parent_loc: The location of the parent node only relevant for Const nodes, defaults to Loc().
        :type parent_loc: Loc, optional
        """
        try:
            outputs = {
                output: None for output in graph.node_outputs[graph.output_idx()]
            }
        except TierkreisError:
            outputs = {}

        self.nodes[parent_loc] = NodeData(
            definition=Eval((-1, "body"), {}),
            call_args=None,
            is_done=False,
            has_error=False,
            metadata={},
            error_logs="",
            outputs=outputs,
        )
        self.nodes[parent_loc].metadata["start_time"] = str(datetime.now())
        self.nodes[parent_loc.N(-1)] = NodeData(
            definition=None,
            call_args=None,
            is_done=False,
            has_error=False,
            metadata={},
            error_logs="",
            outputs={"body": graph.model_dump_json().encode()},
        )

    def _node_from_loc(self, node_location: Loc) -> NodeData:
        if node_location in self.nodes:
            return self.nodes[node_location]
        graph = self.graph
        if len(graph.nodes) == 0:
            raise TierkreisError("Cannot convert location to node. Reason: Empty Graph")
        previous_graph = graph
        node_id = 0
        node: NodeDef | None = graph.nodes[0]
        loc = Loc()
        for step in node_location.steps():
            if step == "-":
                continue
            _, node_id = step

            loc = Loc(loc + "." + step[0] + str(step[1]))
            if loc in self.nodes:
                #
                node = self.nodes[loc].definition
                if node is None:
                    graph = self.nodes[loc].outputs["body"]
                    continue
                match node.type:
                    case "eval":
                        if node.graph[0] == -1:
                            continue
                        graph = graph.nodes[node.graph[0]].value
                    case "map" | "loop":
                        graph = graph.nodes[node.body[0]].value
                    case (
                        "const" | "function" | "input" | "output" | "ifelse" | "eifelse"
                    ):
                        pass
                    case _:
                        assert_never(node)
                continue

            if isinstance(node_id, str):
                if "-" in node_id:
                    node_id = node_id.split("-")[1]
                if node_id == "*":  # potentially "*" in node_id
                    node_id = "0"
                try:
                    node_id = int(node_id)
                except ValueError:
                    node_id = 0

            node = graph.nodes[node_id]
            previous_graph = graph
            match node.type:
                case "eval":
                    graph = graph.nodes[node.graph[0]].value
                    self.nodes[loc.N(-1)] = NodeData(
                        outputs={"body": graph.model_dump_json().encode()},
                    )

                case "loop":
                    graph = graph.nodes[node.body[0]].value
                    try:
                        outputs = (
                            {
                                output: None
                                for output in graph.node_outputs[graph.output_idx()]
                            },
                        )
                    except TierkreisError:
                        outputs = {}
                    self.nodes[loc.L(0)] = NodeData(
                        definition=Eval((-1, "body"), {}), outputs=outputs
                    )
                    self.nodes[loc.L(0).N(-1)] = NodeData(
                        outputs={"body": graph.model_dump_json().encode()},
                    )

                case "map":
                    graph = graph.nodes[node.body[0]].value
                    try:
                        outputs = (
                            {
                                output: None
                                for output in graph.node_outputs[graph.output_idx()]
                            },
                        )
                    except TierkreisError:
                        outputs = {}
                    if "*" in outputs:
                        outputs["0"] = None
                    self.nodes[loc.M("0")] = NodeData(
                        definition=Eval((-1, "body"), {}),
                        outputs=outputs,
                    )
                    self.nodes[loc.M("0").N(-1)] = NodeData(
                        outputs={"body": graph.model_dump_json().encode()},
                    )
                case "const" | "function" | "input" | "output" | "ifelse" | "eifelse":
                    pass
                case _:
                    assert_never(node)
        # Have found the node, now populate the node data correctly
        if node_location not in self.nodes:
            outputs = {output: None for output in previous_graph.node_outputs[node_id]}
            if "*" in outputs:
                outputs["0"] = None
            self.nodes[node_location] = NodeData(
                definition=node,
                outputs=outputs,
            )

        return self.nodes[node_location]
