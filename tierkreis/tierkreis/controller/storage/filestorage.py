import json
import os
import shutil
from pathlib import Path
from time import time_ns
from typing import Any
from uuid import UUID

from tierkreis.controller.data.graph import NodeDef, NodeDefModel, PortID
from tierkreis.controller.data.location import (
    Loc,
    OutputLoc,
    WorkerCallArgs,
)
from tierkreis.exceptions import TierkreisError


class ControllerFileStorage:
    def __init__(
        self,
        workflow_id: UUID,
        name: str | None = None,
        tierkreis_directory: Path = Path.home() / ".tierkreis" / "checkpoints",
        do_cleanup: bool = False,
    ) -> None:
        self.workflow_id = workflow_id
        self.workflow_dir: Path = tierkreis_directory / str(workflow_id)
        self.workflow_dir.mkdir(parents=True, exist_ok=True)
        self.logs_path = self.workflow_dir / "logs"
        self.name = name
        if do_cleanup:
            self.clean_graph_files()

    def _nodedef_path(self, node_location: Loc) -> Path:
        path = self.workflow_dir / str(node_location) / "nodedef"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _worker_call_args_path(self, node_location: Loc) -> Path:
        path = self.workflow_dir / str(node_location) / "definition"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _metadata_path(self, node_location: Loc) -> Path:
        path = self.workflow_dir / str(node_location) / "_metadata"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _outputs_dir(self, node_location: Loc) -> Path:
        path = self.workflow_dir / str(node_location) / "outputs"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _output_path(self, node_location: Loc, port_name: PortID) -> Path:
        path = self._outputs_dir(node_location) / port_name
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _done_path(self, node_location: Loc) -> Path:
        path = self.workflow_dir / str(node_location) / "_done"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _error_path(self, node_location: Loc) -> Path:
        path = self.workflow_dir / str(node_location) / "_error"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _error_logs_path(self, node_location: Loc) -> Path:
        path = self.workflow_dir / str(node_location) / "errors"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def clean_graph_files(self) -> None:
        uid = os.getuid()
        tmp_dir = Path(f"/tmp/{uid}/tierkreis/archive/{self.workflow_id}/{time_ns()}")
        tmp_dir.mkdir(parents=True)
        if self.workflow_dir.exists():
            shutil.move(self.workflow_dir, tmp_dir)

    def add_input(self, port_name: PortID, value: bytes) -> Loc:
        input_loc = Loc().N(-1)
        path = self._output_path(input_loc, port_name)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb+") as fh:
            fh.write(bytes(value))

        return input_loc

    def write_node_def(self, node_location: Loc, node: NodeDef):
        with open(self._nodedef_path(node_location), "w+") as fh:
            fh.write(NodeDefModel(root=node).model_dump_json())

    def read_node_def(self, node_location: Loc) -> NodeDef:
        with open(self._nodedef_path(node_location)) as fh:
            return NodeDefModel(**json.load(fh)).root

    def write_worker_call_args(
        self,
        node_location: Loc,
        function_name: str,
        inputs: dict[PortID, OutputLoc],
        output_list: list[PortID],
    ) -> Path:
        node_definition_path = self._worker_call_args_path(node_location)
        node_definition = WorkerCallArgs(
            function_name=function_name,
            inputs={
                k: self._output_path(loc, port) for k, (loc, port) in inputs.items()
            },
            outputs={k: self._output_path(node_location, k) for k in output_list},
            output_dir=self._outputs_dir(node_location),
            done_path=self._done_path(node_location),
            error_path=self._error_path(node_location),
            logs_path=self.logs_path,
        )
        with open(node_definition_path, "w+") as fh:
            fh.write(node_definition.model_dump_json())

        if (parent := node_location.parent()) is not None:
            self._metadata_path(parent).touch()

        return node_definition_path

    def read_worker_call_args(self, node_location: Loc) -> WorkerCallArgs:
        node_definition_path = self._worker_call_args_path(node_location)
        with open(node_definition_path, "r") as fh:
            return WorkerCallArgs(**json.load(fh))

    def link_outputs(
        self,
        new_location: Loc,
        new_port: PortID,
        old_location: Loc,
        old_port: PortID,
    ) -> None:
        new_dir = self._output_path(new_location, new_port)
        new_dir.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.link(self._output_path(old_location, old_port), new_dir)
        except OSError as e:
            raise TierkreisError(
                "Workflow already exists. Try running with a different ID or do_cleanup."
            ) from e

    def is_output_ready(self, node_location: Loc, output_name: PortID) -> bool:
        return self._output_path(node_location, output_name).exists()

    def write_output(
        self, node_location: Loc, output_name: PortID, value: bytes
    ) -> Path:
        output_path = self._output_path(node_location, output_name)
        with open(output_path, "wb+") as fh:
            fh.write(bytes(value))
        return output_path

    def read_output(self, node_location: Loc, output_name: PortID) -> bytes:
        with open(self._output_path(node_location, output_name), "rb") as fh:
            return fh.read()

    def read_errors(self, node_location: Loc) -> str:
        if not self._error_logs_path(node_location).exists():
            return ""
        with open(self._error_logs_path(node_location), "r") as fh:
            return fh.read()

    def write_node_errors(self, node_location: Loc, error_logs: str) -> None:
        with open(self._error_logs_path(node_location), "w+") as fh:
            fh.write(error_logs)

    def read_output_ports(self, node_location: Loc) -> list[PortID]:
        dir_list = list(self._outputs_dir(node_location).iterdir())
        dir_list.sort()
        return [x.name for x in dir_list if x.is_file()]

    def is_node_started(self, node_location: Loc) -> bool:
        return Path(self._worker_call_args_path(node_location)).exists()

    def is_node_finished(self, node_location: Loc) -> bool:
        return self._done_path(node_location).exists()

    def node_has_error(self, node_location: Loc) -> bool:
        return self._error_path(node_location).exists()

    def mark_node_finished(self, node_location: Loc) -> None:
        self._done_path(node_location).touch()

        if (parent := node_location.parent()) is not None:
            self._metadata_path(parent).touch()

    def write_metadata(self, node_location: Loc) -> None:
        with open(self._metadata_path(node_location), "w+") as fh:
            fh.write(json.dumps({"name": self.name}))

    def read_metadata(self, node_location: Loc) -> dict[str, Any]:
        with open(self._metadata_path(node_location)) as fh:
            return json.load(fh)
