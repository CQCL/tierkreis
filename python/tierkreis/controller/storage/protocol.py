from pathlib import Path
from typing import Any, Protocol

from tierkreis.controller.data.graph import NodeDef, PortID
from tierkreis.controller.data.location import (
    Loc,
    OutputLoc,
    WorkerCallArgs,
)


class ControllerStorage(Protocol):
    logs_path: Path

    def write_node_def(self, node_location: Loc, node: NodeDef) -> None: ...
    def read_node_def(self, node_location: Loc) -> NodeDef: ...

    def write_worker_call_args(
        self,
        node_location: Loc,
        function_name: str,
        inputs: dict[PortID, OutputLoc],
        output_list: list[PortID],
    ) -> Path: ...
    def read_worker_call_args(self, node_location: Loc) -> WorkerCallArgs: ...

    def read_errors(self, node_location: Loc) -> str: ...
    def node_has_error(self, node_location: Loc) -> bool: ...
    def write_node_errors(self, node_location: Loc, error_logs: str) -> None: ...

    def mark_node_finished(self, node_location: Loc) -> None: ...
    def is_node_finished(self, node_location: Loc) -> bool: ...

    def link_outputs(
        self,
        new_location: Loc,
        new_port: PortID,
        old_location: Loc,
        old_port: PortID,
    ) -> None: ...

    def write_output(
        self, node_location: Loc, output_name: PortID, value: bytes
    ) -> Path: ...

    def read_output(self, node_location: Loc, output_name: PortID) -> bytes: ...

    def read_output_ports(self, node_location: Loc) -> list[PortID]: ...

    def is_node_started(self, node_location: Loc) -> bool: ...

    def read_metadata(self, node_location: Loc) -> dict[str, Any]: ...

    def write_metadata(self, node_location: Loc) -> None: ...
