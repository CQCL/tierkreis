import json
from pathlib import Path
from typing import Any, Protocol

from tierkreis.controller.data.core import PortID
from tierkreis.controller.data.graph import NodeDef, NodeDefModel
from tierkreis.controller.data.location import Loc, OutputLoc, WorkerCallArgs
from tierkreis.exceptions import TierkreisError


class PathStorageBackend(Protocol):
    workflow_dir: Path
    logs_path: Path
    name: str

    def _delete(self) -> None: ...
    def _exists(self, path: Path) -> bool: ...
    def _link(self, src: Path, dst: Path) -> None: ...
    def _read(self, path: Path) -> bytes: ...
    def _touch(self, path: Path, is_dir: bool = False) -> None: ...
    def _write(self, path: Path, value: bytes) -> None: ...


class PathStorageBase(PathStorageBackend):
    def _nodedef_path(self, node_location: Loc) -> Path:
        return self.workflow_dir / str(node_location) / "nodedef"

    def _worker_call_args_path(self, node_location: Loc) -> Path:
        return self.workflow_dir / str(node_location) / "definition"

    def _metadata_path(self, node_location: Loc) -> Path:
        return self.workflow_dir / str(node_location) / "_metadata"

    def _outputs_dir(self, node_location: Loc) -> Path:
        return self.workflow_dir / str(node_location) / "outputs"

    def _output_path(self, node_location: Loc, port_name: PortID) -> Path:
        return self._outputs_dir(node_location) / port_name

    def _done_path(self, node_location: Loc) -> Path:
        return self.workflow_dir / str(node_location) / "_done"

    def _error_path(self, node_location: Loc) -> Path:
        return self.workflow_dir / str(node_location) / "_error"

    def _error_logs_path(self, node_location: Loc) -> Path:
        return self.workflow_dir / str(node_location) / "errors"

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
        self._touch(self._outputs_dir(node_location), True)

        if (parent := node_location.parent()) is not None:
            self._touch(self._metadata_path(parent))

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
        try:
            self._link(self._output_path(old_location, old_port), new_dir)
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
        return self._exists(self._output_path(node_location, output_name))

    def write_output(
        self, node_location: Loc, output_name: PortID, value: bytes
    ) -> Path:
        output_path = self._output_path(node_location, output_name)
        self._write(output_path, value)
        return output_path

    def read_output(self, node_location: Loc, output_name: PortID) -> bytes:
        return self._read(self._output_path(node_location, output_name))

    def read_errors(self, node_location: Loc) -> str:
        if not self._exists(self._error_logs_path(node_location)):
            return ""
        return self._read(self._error_logs_path(node_location)).decode()

    def write_node_errors(self, node_location: Loc, error_logs: str) -> None:
        self._write(self._error_logs_path(node_location), error_logs.encode())

    def read_output_ports(self, node_location: Loc) -> list[PortID]:
        dir_list = list(self._outputs_dir(node_location).iterdir())
        dir_list.sort()
        return [x.name for x in dir_list if x.is_file()]

    def is_node_started(self, node_location: Loc) -> bool:
        return self._exists(Path(self._nodedef_path(node_location)))

    def is_node_finished(self, node_location: Loc) -> bool:
        return self._exists(self._done_path(node_location))

    def node_has_error(self, node_location: Loc) -> bool:
        return self._exists(self._error_path(node_location))

    def mark_node_finished(self, node_location: Loc) -> None:
        self._touch(self._done_path(node_location))

        if (parent := node_location.parent()) is not None:
            self._touch(self._metadata_path(parent))

    def write_metadata(self, node_location: Loc) -> None:
        bs = json.dumps({"name": self.name}).encode()
        self._write(self._metadata_path(node_location), bs)

    def read_metadata(self, node_location: Loc) -> dict[str, Any]:
        bs = self._read(self._metadata_path(node_location))
        return json.loads(bs)
