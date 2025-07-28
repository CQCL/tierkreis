from collections import defaultdict
from pathlib import Path
from uuid import UUID
from typing import Any, assert_never
import shutil
import os
from time import time_ns

from pydantic import BaseModel, Field

from tierkreis.controller.data.core import PortID, ValueRef
from tierkreis.controller.data.graph import Const, Eval, GraphData, NodeDef
from tierkreis.controller.data.location import (
    Loc,
    OutputLoc,
    WorkerCallArgs,
)
from tierkreis.exceptions import TierkreisError


class NodeData(BaseModel):
    definition: NodeDef | None = None
    call_args: WorkerCallArgs | None = None
    is_done: bool = False
    has_error: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
    error_logs: str = ""
    outputs: dict[PortID, bytes | None] = Field(default_factory=dict)


class ControllerInMemoryStorage:
    def __init__(
        self,
        workflow_id: UUID,
        name: str | None = None,
    ) -> None:
        self.work_dir = Path.home() / ".tierkreis" / "tmp"
        self.clean_graph_files()
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.workflow_id = workflow_id
        self.logs_path = self.work_dir / "logs"
        self.logs_path.touch()
        self.name = name
        self.nodes: dict[Loc, NodeData] = defaultdict(lambda: NodeData())

    def write_node_def(self, node_location: Loc, node: NodeDef) -> None:
        self.nodes[node_location].definition = node

    def read_node_def(self, node_location: Loc) -> NodeDef:
        if result := self.nodes[node_location].definition:
            return result
        raise TierkreisError(f"Node definition of {node_location} not found.")

    def write_worker_call_args(
        self,
        node_location: Loc,
        function_name: str,
        inputs: dict[PortID, OutputLoc],
        output_list: list[PortID],
    ) -> Path:
        node_path = Path(node_location)
        call_args = WorkerCallArgs(
            function_name=function_name,
            inputs={k: Path(loc) / port for k, (loc, port) in inputs.items()},
            outputs={k: node_path / k for k in output_list},
            output_dir=node_path,
            done_path=node_path,
            error_path=node_path,
            logs_path=self.logs_path,
        )
        for port in output_list:
            # workaround
            self.nodes[node_location].outputs[port] = None
        self.nodes[node_location].call_args = call_args
        if (parent := node_location.parent()) is not None:
            self.nodes[parent].metadata = {}

        return node_path

    def read_worker_call_args(self, node_location: Loc) -> WorkerCallArgs:
        if result := self.nodes[node_location].call_args:
            return result
        raise TierkreisError(
            f"Node location {node_location} doesn't have a associate call args."
        )

    def read_errors(self, node_location: Loc) -> str:
        if errors := self.nodes[node_location].error_logs:
            return errors
        return ""

    def node_has_error(self, node_location: Loc) -> bool:
        return self.nodes[node_location].has_error

    def write_node_errors(self, node_location: Loc, error_logs: str) -> None:
        self.nodes[node_location].error_logs = error_logs

    def mark_node_finished(self, node_location: Loc) -> None:
        self.nodes[node_location].is_done = True

    def is_node_finished(self, node_location: Loc) -> bool:
        return self.nodes[node_location].is_done

    def link_outputs(
        self,
        new_location: Loc,
        new_port: PortID,
        old_location: Loc,
        old_port: PortID,
    ) -> None:
        self.nodes[new_location].outputs[new_port] = self.nodes[old_location].outputs[
            old_port
        ]

    def write_output(
        self, node_location: Loc, output_name: PortID, value: bytes
    ) -> Path:
        self.nodes[node_location].outputs[output_name] = value
        return Path(node_location) / output_name

    def read_output(self, node_location: Loc, output_name: PortID) -> bytes:
        if output_name in self.nodes[node_location].outputs:
            if output := self.nodes[node_location].outputs[output_name]:
                return output
            return b""
        raise TierkreisError(f"No output named {output_name} in node {node_location}")

    def read_output_ports(self, node_location: Loc) -> list[PortID]:
        return list(
            filter(lambda k: k != "*", self.nodes[node_location].outputs.keys())
        )

    def is_node_started(self, node_location: Loc) -> bool:
        return self.nodes[node_location].definition is not None

    def read_metadata(self, node_location: Loc) -> dict[str, Any]:
        return self.nodes[node_location].metadata

    def write_metadata(self, node_location: Loc) -> None:
        self.nodes[node_location].metadata = {"name": self.name}

    def clean_graph_files(self) -> None:
        uid = os.getuid()
        tmp_dir = Path(f"/tmp/{uid}/tierkreis/archive/{time_ns()}")
        tmp_dir.mkdir(parents=True)
        if self.work_dir.exists():
            shutil.move(self.work_dir, tmp_dir)

    def evaluate_symbolic(self, graph: GraphData, parent_loc: Loc = Loc()) -> None:
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
        self.nodes[parent_loc] = NodeData(
            definition=Eval((-1, "body"), {}),
            call_args=None,
            is_done=False,
            has_error=False,
            metadata={},
            error_logs="",
            outputs={output: None for output in graph.node_outputs[graph.output_idx()]},
        )
        self.nodes[parent_loc.N(-1)] = NodeData(
            definition=None,
            call_args=None,
            is_done=False,
            has_error=False,
            metadata={},
            error_logs="",
            outputs={"body": graph.model_dump_json().encode()},
        )
        self._evaluate_symbolic(graph, parent_loc)

    def _evaluate_symbolic(self, graph: GraphData, parent_loc: Loc = Loc()) -> None:
        unfinished_inputs = [((graph.output_idx(), ""), parent_loc)]
        for input, parent in unfinished_inputs:
            output_id = input[0]
            output_node = graph.nodes[output_id]
            outputs = list(graph.node_outputs[output_id])
            loc = parent.N(output_id)
            if "*" in outputs:
                outputs.append("0")
            self.nodes[loc] = NodeData(
                definition=output_node,
                call_args=None,
                is_done=False,
                has_error=False,
                metadata={},
                error_logs="",
                outputs={output: None for output in outputs},
            )
            new_unfinished_inputs = self._in_edges(output_node, output_id, parent)
            unfinished_inputs += new_unfinished_inputs

    def _in_edges(
        self, node: NodeDef, node_id: int, parent: Loc
    ) -> list[tuple[ValueRef, Loc]]:
        """Mimics tierkreis.controller.storage.adjacency.in_edges.
        This lets us know which nodes are the inputs of the current node.
        """
        parents = [(x, parent) for x in node.inputs.values()]
        node_loc = parent.N(node_id)
        match node.type:
            case "eval":
                parents.append((node.graph, node_loc))
            case "loop":
                parents.append((node.body, node_loc))
            case "map":
                # Unevaluated maps have a body but no child element to evaluate it
                # We add the first child "0" to allow visualization of the body
                self.nodes[node_loc.M("0")] = NodeData(
                    definition=Eval((-1, "body"), {})
                )
                parents.append((node.body, node_loc))
            case "ifelse" | "eifelse":
                # We want to see conditional branches in both cases
                parents.append((node.pred, node_loc))
                parents.append((node.if_true, node_loc))
                parents.append((node.if_false, node_loc))
            case "const":
                # Const nodes can be graphs themselves, so we need to handle them
                self._handle_const(node, node_id, parent)
            case "function" | "input" | "output":
                pass
            case _:
                assert_never(node)

        return parents

    def _handle_const(self, node: Const, node_id: int, parent: Loc) -> None:
        if parent.parent() is None:
            raise TierkreisError(
                f"Node {node_id} with value {node.value} cannot be a graph output without a parent."
            )
        value: GraphData | None = None
        # Try to load a nested graph from value
        if isinstance(node.value, GraphData):
            value = node.value
        elif isinstance(node.value, dict):
            try:
                value = GraphData(**node.value)
            except TypeError:
                raise TierkreisError(f"Cannot convert {node}s value to GraphData.")
        if value is None:
            # not a graph
            return

        self.nodes[parent.parent().N(node_id)] = NodeData(  # type: ignore
            definition=Const(value),
            outputs={"value": value.model_dump_json().encode()},
        )

        if parent.M("0") in self.nodes:
            # This is a map node
            parent = parent.M("0")
        self.evaluate_symbolic(value, parent)
