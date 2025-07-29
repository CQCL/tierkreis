import logging
import importlib.util
from pathlib import Path

from tierkreis.controller.data.location import Loc, WorkerCallArgs
from tierkreis.controller.storage.in_memory import ControllerInMemoryStorage
from tierkreis.exceptions import TierkreisError


logger = logging.getLogger(__name__)


# Redefined else we have a circular import
class InMemoryWorkerStorage:
    def __init__(self, controller_storage: ControllerInMemoryStorage) -> None:
        self.controller_storage = controller_storage

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


class InMemoryExecutor:
    def __init__(self, registry_path: Path, storage: ControllerInMemoryStorage) -> None:
        self.registry_path = registry_path
        self.storage = storage

    def run(
        self,
        launcher_name: str,
        node_definition_path: Path,
    ) -> None:
        logging.basicConfig(
            format="%(asctime)s: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
            filemode="a",
            level=logging.INFO,
        )
        logger.info("START %s %s", launcher_name, node_definition_path)
        node_location = Loc(str(node_definition_path))
        call_args = self.storage.read_worker_call_args(node_location)

        spec = importlib.util.spec_from_file_location(
            "in_memory", self.registry_path / launcher_name / "main.py"
        )
        if spec is None or spec.loader is None:
            raise TierkreisError(
                f"Couldn't load main.py in {self.registry_path / launcher_name}"
            )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        worker_storage = InMemoryWorkerStorage(self.storage)
        module.worker.storage = worker_storage
        module.worker.functions[call_args.function_name](call_args)
        self.storage.mark_node_finished(node_location)
