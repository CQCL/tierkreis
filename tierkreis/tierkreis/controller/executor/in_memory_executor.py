import logging
import importlib.util
from pathlib import Path

from tierkreis.controller.data.core import PortID
from tierkreis.controller.data.location import Loc, WorkerCallArgs
from tierkreis.controller.storage.in_memory import ControllerInMemoryStorage
from tierkreis.exceptions import TierkreisError


logger = logging.getLogger(__name__)


# Redefined else we have a circular import
class InMemoryWorkerStorage:
    def __init__(self, controller_storage: ControllerInMemoryStorage) -> None:
        self.controller_storage = controller_storage

    def read_call_args(self, path: Path) -> WorkerCallArgs:
        loc = Loc(str(path))
        return self.controller_storage.read_worker_call_args(loc)

    def read_input(self, path: Path) -> bytes:
        strpath = str(path).split("/")
        return self.controller_storage.read_output(Loc(strpath[0]), PortID(strpath[1]))

    def write_output(self, path: Path, value: bytes) -> None:
        strpath = str(path).split("/")
        self.controller_storage.write_output(Loc(strpath[0]), PortID(strpath[1]), value)

    def glob(self, path_string: str) -> list[str]:
        strpath = str(path_string).split("/")
        outputs = [
            str(key) for key in self.controller_storage.nodes[Loc(strpath[0])].outputs
        ]
        outputs = filter(lambda o: o.startswith(strpath[1][:-1]), outputs)
        return [strpath[0] + "/" + out for out in outputs]


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
