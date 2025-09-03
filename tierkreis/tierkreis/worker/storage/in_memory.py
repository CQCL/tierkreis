import logging
from pathlib import Path

from tierkreis.controller.data.location import WorkerCallArgs
from tierkreis.controller.storage.in_memory import ControllerInMemoryStorage
from tierkreis.exceptions import TierkreisError


logger = logging.getLogger(__name__)


class InMemoryWorkerStorage:
    def __init__(self, controller_storage: ControllerInMemoryStorage) -> None:
        self.controller_storage = controller_storage

    def resolve(self, path: Path | str) -> Path:
        return Path(path)

    def read_call_args(self, path: Path) -> WorkerCallArgs:
        loc = self.controller_storage.path_to_loc(path)[0]
        return self.controller_storage.read_worker_call_args(loc)

    def read_input(self, path: Path) -> bytes:
        loc, port = self.controller_storage.path_to_loc(path)
        if port is None:
            raise TierkreisError(f"Path {path} does not specify a port.")
        return self.controller_storage.read_output(loc, port)

    def write_output(self, path: Path, value: bytes) -> None:
        loc, port = self.controller_storage.path_to_loc(path)
        if port is None:
            raise TierkreisError(f"Path {path} does not specify a port.")
        self.controller_storage.write_output(loc, port, value)

    def glob(self, path_string: str) -> list[str]:
        loc, port = self.controller_storage.path_to_loc(Path(path_string))
        path = self.controller_storage.loc_to_path(loc)
        outputs = [str(key) for key in self.controller_storage.nodes[path].outputs]
        if port is not None:
            outputs = filter(lambda o: o.startswith(port[:-1]), outputs)
        return [loc + "/" + out for out in outputs]

    def mark_done(self, path: Path) -> None:
        loc, _ = self.controller_storage.path_to_loc(path)
        self.controller_storage.mark_node_finished(loc)

    def write_error(self, path: Path, error_logs: str) -> None:
        loc, _ = self.controller_storage.path_to_loc(path)
        self.controller_storage.write_node_errors(loc, error_logs)
