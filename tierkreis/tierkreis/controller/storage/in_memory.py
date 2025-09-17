from collections import defaultdict
from datetime import datetime
from pathlib import Path
from uuid import UUID
from typing import Any
import shutil
import os
from time import time_ns

from pydantic import BaseModel, Field

from tierkreis.controller.data.core import PortID
from tierkreis.controller.data.graph import NodeDef
from tierkreis.controller.data.location import (
    Loc,
    OutputLoc,
    WorkerCallArgs,
)
from tierkreis.exceptions import TierkreisError


class NodeData(BaseModel):
    """Internal storage class to store all necessary node information."""

    definition: NodeDef | None = None
    call_args: WorkerCallArgs | None = None
    is_done: bool = False
    has_error: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
    error_logs: str = ""
    outputs: dict[PortID, bytes | None] = Field(default_factory=dict)
    started: str | None = None
    finished: str | None = None


class ControllerInMemoryStorage:
    """In-memory storage for the controller.

    All information is kept in a local dictionary.
    Invalid read operations raise a TierkreisError.

    Implements: :py:class:`tierkreis.controller.storage.protocol.ControllerStorage`
    """

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
        self.nodes: dict[Path, NodeData] = defaultdict(lambda: NodeData())

    def loc_to_path(self, location: Loc, port: PortID | None = None) -> Path:
        # Directly convert, not a real filesystem path
        if port is not None:
            return Path(location) / port
        return Path(location)

    def path_to_loc(self, path: Path) -> tuple[Loc, PortID | None]:
        # assumes the path is in the format 'location/port'
        parts = path.parts
        if len(parts) == 1:
            return Loc(parts[0]), None
        elif len(parts) == 2:
            return Loc(parts[0]), PortID(parts[1])
        else:
            raise ValueError(f"Invalid path format: {path}")

    def write_node_def(self, node_location: Loc, node: NodeDef) -> None:
        self.nodes[self.loc_to_path(node_location)].definition = node
        self.nodes[self.loc_to_path(node_location)].started = datetime.now().isoformat()

    def read_node_def(self, node_location: Loc) -> NodeDef:
        if result := self.nodes[self.loc_to_path(node_location)].definition:
            return result
        raise TierkreisError(f"Node definition of {node_location} not found.")

    def write_worker_call_args(
        self,
        node_location: Loc,
        function_name: str,
        inputs: dict[PortID, OutputLoc],
        output_list: list[PortID],
    ) -> Path:
        node_path = self.loc_to_path(node_location)
        call_args = WorkerCallArgs(
            function_name=function_name,
            inputs={
                k: self.loc_to_path(loc, port) for k, (loc, port) in inputs.items()
            },
            outputs={k: self.loc_to_path(node_location, k) for k in output_list},
            output_dir=node_path,
            done_path=node_path,
            error_path=node_path,
            logs_path=self.logs_path,
        )
        for port in output_list:
            # workaround
            self.nodes[node_path].outputs[port] = None
        self.nodes[node_path].call_args = call_args
        if (parent := node_location.parent()) is not None:
            self.nodes[self.loc_to_path(parent)].metadata = {}

        return node_path

    def read_worker_call_args(self, node_location: Loc) -> WorkerCallArgs:
        if result := self.nodes[self.loc_to_path(node_location)].call_args:
            return result
        raise TierkreisError(
            f"Node location {node_location} doesn't have a associate call args."
        )

    def read_errors(self, node_location: Loc) -> str:
        if errors := self.nodes[self.loc_to_path(node_location)].error_logs:
            return errors
        return ""

    def node_has_error(self, node_location: Loc) -> bool:
        return self.nodes[self.loc_to_path(node_location)].has_error

    def write_node_errors(self, node_location: Loc, error_logs: str) -> None:
        self.nodes[self.loc_to_path(node_location)].error_logs = error_logs

    def mark_node_finished(self, node_location: Loc) -> None:
        self.nodes[self.loc_to_path(node_location)].is_done = True
        self.nodes[
            self.loc_to_path(node_location)
        ].finished = datetime.now().isoformat()

    def is_node_finished(self, node_location: Loc) -> bool:
        return self.nodes[self.loc_to_path(node_location)].is_done

    def link_outputs(
        self,
        new_location: Loc,
        new_port: PortID,
        old_location: Loc,
        old_port: PortID,
    ) -> None:
        self.nodes[self.loc_to_path(new_location)].outputs[new_port] = self.nodes[
            self.loc_to_path(old_location)
        ].outputs[old_port]

    def write_output(
        self, node_location: Loc, output_name: PortID, value: bytes
    ) -> Path:
        self.nodes[self.loc_to_path(node_location)].outputs[output_name] = value
        return Path(node_location) / output_name

    def read_output(self, node_location: Loc, output_name: PortID) -> bytes:
        if output_name in self.nodes[self.loc_to_path(node_location)].outputs:
            if output := self.nodes[self.loc_to_path(node_location)].outputs[
                output_name
            ]:
                return output
            return b"null"
        raise TierkreisError(f"No output named {output_name} in node {node_location}")

    def read_output_ports(self, node_location: Loc) -> list[PortID]:
        return list(
            filter(
                lambda k: k != "*",
                self.nodes[self.loc_to_path(node_location)].outputs.keys(),
            )
        )

    def is_node_started(self, node_location: Loc) -> bool:
        return self.nodes[self.loc_to_path(node_location)].definition is not None

    def read_metadata(self, node_location: Loc) -> dict[str, Any]:
        return self.nodes[self.loc_to_path(node_location)].metadata

    def write_metadata(self, node_location: Loc) -> None:
        self.nodes[self.loc_to_path(node_location)].metadata = {
            "name": self.name,
            "start_time": datetime.now().isoformat(),
        }

    def read_started_time(self, node_location: Loc) -> str | None:
        return self.nodes[self.loc_to_path(node_location)].started

    def read_finished_time(self, node_location: Loc) -> str | None:
        return self.nodes[self.loc_to_path(node_location)].finished

    def clean_graph_files(self) -> None:
        uid = os.getuid()
        tmp_dir = Path(f"/tmp/{uid}/tierkreis/archive/{time_ns()}")
        tmp_dir.mkdir(parents=True)
        if self.work_dir.exists():
            shutil.move(self.work_dir, tmp_dir)
