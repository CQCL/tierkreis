import json
import os
import shutil
from datetime import datetime
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
from tierkreis.paths import Paths


class ControllerFileStorage:
    """Default file-base storage for the controller.

    All information is stored in the file system, by default in `~/.tierkreis/checkpoints`.
    Uses file systems links to map outputs to new nodes.
    Invalid read operations raise a FileNotFoundError.

    Implements: :py:class:`tierkreis.controller.storage.protocol.ControllerStorage`
    """

    def __init__(
        self,
        workflow_id: UUID,
        name: str | None = None,
        tierkreis_directory: Path = Path.home() / ".tierkreis" / "checkpoints",
        do_cleanup: bool = False,
    ) -> None:
        self.workflow_id = workflow_id
        self.tkr_dir = tierkreis_directory
        self.workflow_dir: Path = tierkreis_directory / str(workflow_id)
        self.workflow_dir.mkdir(parents=True, exist_ok=True)
        self.logs_path = self.workflow_dir / "logs"
        self.name = name
        if do_cleanup:
            self.clean_graph_files()
        self.paths = Paths(workflow_id, tierkreis_directory)

    def clean_graph_files(self) -> None:
        uid = os.getuid()
        tmp_dir = Path(f"/tmp/{uid}/tierkreis/archive/{self.workflow_id}/{time_ns()}")
        tmp_dir.mkdir(parents=True)
        if self.workflow_dir.exists():
            shutil.move(self.workflow_dir, tmp_dir)

    def write_node_def(self, node_location: Loc, node: NodeDef):
        with open(self.paths.nodedef_path(node_location), "w+") as fh:
            fh.write(NodeDefModel(root=node).model_dump_json())

    def read_node_def(self, node_location: Loc) -> NodeDef:
        with open(self.paths.nodedef_path(node_location)) as fh:
            return NodeDefModel(**json.load(fh)).root

    def write_worker_call_args(
        self,
        node_location: Loc,
        function_name: str,
        inputs: dict[PortID, OutputLoc],
        output_list: list[PortID],
    ) -> Path:
        call_args_path = self.paths.worker_call_args_path(node_location)
        node_definition = WorkerCallArgs(
            function_name=function_name,
            inputs={
                k: self.paths.output_path(loc, port).relative_to(self.tkr_dir)
                for k, (loc, port) in inputs.items()
            },
            outputs={
                k: self.paths.output_path(node_location, k).relative_to(self.tkr_dir)
                for k in output_list
            },
            output_dir=self.paths.outputs_dir(node_location).relative_to(self.tkr_dir),
            done_path=self.paths.done_path(node_location).relative_to(self.tkr_dir),
            error_path=self.paths.error_path(node_location).relative_to(self.tkr_dir),
            logs_path=self.logs_path.relative_to(self.tkr_dir),
        )
        with open(call_args_path, "w+") as fh:
            fh.write(node_definition.model_dump_json())

        if (parent := node_location.parent()) is not None:
            self.paths.metadata_path(parent).touch()

        return call_args_path.relative_to(self.tkr_dir)

    def read_worker_call_args(self, node_location: Loc) -> WorkerCallArgs:
        node_definition_path = self.paths.worker_call_args_path(node_location)
        with open(node_definition_path, "r") as fh:
            return WorkerCallArgs(**json.load(fh))

    def link_outputs(
        self,
        new_location: Loc,
        new_port: PortID,
        old_location: Loc,
        old_port: PortID,
    ) -> None:
        new_dir = self.paths.output_path(new_location, new_port)
        new_dir.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.link(self.paths.output_path(old_location, old_port), new_dir)
        except FileNotFoundError as e:
            raise TierkreisError(
                f"Could not link {e.filename} to {e.filename2}."
                " Possibly a mislabelled variable?"
            )
        except OSError as e:
            raise TierkreisError(
                "Workflow already exists. Try running with a different ID or do_cleanup."
            ) from e

    def write_output(
        self, node_location: Loc, output_name: PortID, value: bytes
    ) -> Path:
        output_path = self.paths.output_path(node_location, output_name)
        with open(output_path, "wb+") as fh:
            fh.write(bytes(value))
        return output_path

    def read_output(self, node_location: Loc, output_name: PortID) -> bytes:
        with open(self.paths.output_path(node_location, output_name), "rb") as fh:
            return fh.read()

    def read_errors(self, node_location: Loc) -> str:
        if not self.paths.error_logs_path(node_location).exists():
            return ""
        with open(self.paths.error_logs_path(node_location), "r") as fh:
            return fh.read()

    def write_node_errors(self, node_location: Loc, error_logs: str) -> None:
        with open(self.paths.error_logs_path(node_location), "w+") as fh:
            fh.write(error_logs)

    def read_output_ports(self, node_location: Loc) -> list[PortID]:
        dir_list = list(self.paths.outputs_dir(node_location).iterdir())
        dir_list.sort()
        return [x.name for x in dir_list if x.is_file()]

    def is_node_started(self, node_location: Loc) -> bool:
        return Path(self.paths.nodedef_path(node_location)).exists()

    def is_node_finished(self, node_location: Loc) -> bool:
        return self.paths.done_path(node_location).exists()

    def node_has_error(self, node_location: Loc) -> bool:
        return self.paths.error_path(node_location).exists()

    def mark_node_finished(self, node_location: Loc) -> None:
        self.paths.done_path(node_location).touch()

        if (parent := node_location.parent()) is not None:
            self.paths.metadata_path(parent).touch()

    def write_metadata(self, node_location: Loc) -> None:
        with open(self.paths.metadata_path(node_location), "w+") as fh:
            fh.write(
                json.dumps(
                    {"name": self.name, "start_time": datetime.now().isoformat()}
                )
            )

    def read_metadata(self, node_location: Loc) -> dict[str, Any]:
        with open(self.paths.metadata_path(node_location)) as fh:
            return json.load(fh)
