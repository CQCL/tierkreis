import json
import os
import shutil
from pathlib import Path
from time import time_ns
from typing import Any
from uuid import UUID

from tierkreis.controller.data.core import PortID
from tierkreis.controller.data.graph import NodeDef, NodeDefModel
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
        return path

    def _worker_call_args_path(self, node_location: Loc) -> Path:
        path = self.workflow_dir / str(node_location) / "definition"
        return path

    def _metadata_path(self, node_location: Loc) -> Path:
        path = self.workflow_dir / str(node_location) / "_metadata"
        return path

    def _outputs_dir(self, node_location: Loc) -> Path:
        path = self.workflow_dir / str(node_location) / "outputs"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _output_path(self, node_location: Loc, port_name: PortID) -> Path:
        path = self._outputs_dir(node_location) / port_name
        return path

    def _done_path(self, node_location: Loc) -> Path:
        path = self.workflow_dir / str(node_location) / "_done"
        return path

    def _error_path(self, node_location: Loc) -> Path:
        path = self.workflow_dir / str(node_location) / "_error"
        return path

    def _error_logs_path(self, node_location: Loc) -> Path:
        path = self.workflow_dir / str(node_location) / "errors"
        return path

    def _read(self, path: Path) -> bytes:
        with open(path, "rb") as fh:
            return fh.read()

    def _write(self, path: Path, value: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb+") as fh:
            fh.write(value)

    def _delete(self) -> None:
        uid = os.getuid()
        tmp_dir = Path(f"/tmp/{uid}/tierkreis/archive/{self.workflow_id}/{time_ns()}")
        tmp_dir.mkdir(parents=True)
        if self.workflow_dir.exists():
            shutil.move(self.workflow_dir, tmp_dir)

    def clean_graph_files(self) -> None:
        self._delete()

    def write_node_def(self, node_location: Loc, node: NodeDef):
        bs = NodeDefModel(root=node).model_dump_json().encode()
        self._write(self._nodedef_path(node_location), bs)

    def read_node_def(self, node_location: Loc) -> NodeDef:
        bs = self._read(self._nodedef_path(node_location))
        return NodeDefModel(**json.loads(bs)).root

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
        self._write(node_definition_path, node_definition.model_dump_json().encode())

        if (parent := node_location.parent()) is not None:
            self._metadata_path(parent).touch()

        return node_definition_path

    def read_worker_call_args(self, node_location: Loc) -> WorkerCallArgs:
        node_definition_path = self._worker_call_args_path(node_location)
        bs = self._read(node_definition_path)
        return WorkerCallArgs(**json.loads(bs))

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
        except FileNotFoundError as e:
            raise TierkreisError(
                f"Could not link {e.filename} to {e.filename2}."
                " Possibly a mislabelled variable?"
            )
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
        self._write(output_path, value)
        return output_path

    def read_output(self, node_location: Loc, output_name: PortID) -> bytes:
        return self._read(self._output_path(node_location, output_name))

    def read_errors(self, node_location: Loc) -> str:
        if not self._error_logs_path(node_location).exists():
            return ""
        return self._read(self._error_logs_path(node_location)).decode()

    def write_node_errors(self, node_location: Loc, error_logs: str) -> None:
        self._write(self._error_logs_path(node_location), error_logs.encode())

    def read_output_ports(self, node_location: Loc) -> list[PortID]:
        dir_list = list(self._outputs_dir(node_location).iterdir())
        dir_list.sort()
        return [x.name for x in dir_list if x.is_file()]

    def is_node_started(self, node_location: Loc) -> bool:
        return Path(self._nodedef_path(node_location)).exists()

    def is_node_finished(self, node_location: Loc) -> bool:
        return self._done_path(node_location).exists()

    def node_has_error(self, node_location: Loc) -> bool:
        return self._error_path(node_location).exists()

    def mark_node_finished(self, node_location: Loc) -> None:
        self._done_path(node_location).touch()

        if (parent := node_location.parent()) is not None:
            self._metadata_path(parent).touch()

    def write_metadata(self, node_location: Loc) -> None:
        bs = json.dumps({"name": self.name}).encode()
        self._write(self._metadata_path(node_location), bs)

    def read_metadata(self, node_location: Loc) -> dict[str, Any]:
        bs = self._read(self._metadata_path(node_location))
        return json.loads(bs)
