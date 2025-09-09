from pathlib import Path
from uuid import UUID
from tierkreis.config import CONFIG
from tierkreis.controller.data.core import PortID
from tierkreis.controller.data.location import Loc


class Paths:
    def __init__(self, workflow_id: UUID, tkr_dir: Path = CONFIG.tkr_dir) -> None:
        self.checkpoints_dir = tkr_dir / "checkpoints"
        self.workflow_id = workflow_id
        self.workflow_dir = self.checkpoints_dir / str(workflow_id)

    def resolve(self, relative_path: Path) -> Path:
        return self.checkpoints_dir / relative_path

    def relative(self, absolute_path: Path) -> Path:
        return absolute_path.relative_to(self.checkpoints_dir)

    def _create_path(self, node_location: Loc, names: list[str]) -> Path:
        path = self.workflow_dir / str(node_location) / "/".join(names)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def nodedef_path(self, node_location: Loc) -> Path:
        return self._create_path(node_location, ["nodedef"])

    def worker_call_args_path(self, node_location: Loc) -> Path:
        return self._create_path(node_location, ["definition"])

    def metadata_path(self, node_location: Loc) -> Path:
        return self._create_path(node_location, ["_metadata"])

    def outputs_dir(self, node_location: Loc) -> Path:
        return self._create_path(node_location, ["outputs"])

    def output_path(self, node_location: Loc, port_name: PortID) -> Path:
        return self._create_path(node_location, ["outputs", port_name])

    def done_path(self, node_location: Loc) -> Path:
        return self._create_path(node_location, ["_done"])

    def error_path(self, node_location: Loc) -> Path:
        return self._create_path(node_location, ["_error"])

    def error_logs_path(self, node_location: Loc) -> Path:
        return self._create_path(node_location, ["errors"])

    def logs_path(self) -> Path:
        return self.workflow_dir / "logs"
