import json
import logging
from logging import getLogger
from pathlib import Path
import sys
from types import TracebackType
from typing import Callable

from tierkreis.codegen import format_namespace
from tierkreis.controller.data.core import (
    PortID,
    TModel,
    TType,
    WorkerFunction,
    bytes_from_ttype,
    dict_from_tmodel,
    ttype_from_bytes,
)
from tierkreis.controller.data.graph import GraphData, inputs_from_tmodel
from tierkreis.controller.data.location import WorkerCallArgs
from tierkreis.exceptions import TierkreisError
from tierkreis.namespace import Namespace
from tierkreis.worker.storage.filestorage import WorkerFileStorage
from tierkreis.worker.storage.protocol import WorkerStorage

logger = getLogger(__name__)


def handle_unhandled_exception(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_traceback: TracebackType | None,
):
    logger.critical(
        "Unhandled exception", exc_info=(exc_type, exc_value, exc_traceback)
    )


class Worker:
    functions: dict[str, Callable[[WorkerCallArgs], None]]
    namespace: Namespace

    def __init__(self, name: str, storage: WorkerStorage | None = None) -> None:
        self.name = name
        self.functions = {}
        self.namespace = Namespace(name=self.name, functions=[])
        if storage is None:
            self.storage: WorkerStorage = WorkerFileStorage()
        else:
            self.storage = storage
        sys.excepthook = handle_unhandled_exception

    def _load_args(self, inputs: dict[str, Path]) -> dict[str, TType]:
        bs = {k: self.storage.read_input(p) for k, p in inputs.items()}
        print(bs)
        return {k: ttype_from_bytes(b) for k, b in bs.items()}

    def _save_results(self, outputs: dict[PortID, Path], results: TModel):
        d = dict_from_tmodel(results)
        logger.error("_saveresults")
        logger.error(d)
        for result_name, path in outputs.items():
            self.storage.write_output(path, bytes_from_ttype(d[result_name]))

    def function(self, name: str | None = None) -> Callable[[WorkerFunction], None]:
        """Register a function with the worker."""

        def function_decorator(func: WorkerFunction) -> None:
            func_name = name if name is not None else func.__name__
            self.namespace.add_from_annotations(func.__name__, func.__annotations__)

            def wrapper(node_definition: WorkerCallArgs):
                kwargs = self._load_args(node_definition.inputs)
                results = func(**kwargs)
                logger.error("results")
                logger.error(results)
                self._save_results(node_definition.outputs, results)

            self.functions[func_name] = wrapper

        return function_decorator

    def run(self, worker_definition_path: Path) -> None:
        """Run a function."""
        node_definition = self.storage.read_call_args(worker_definition_path)

        logging.basicConfig(
            format="%(asctime)s: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
            filename=node_definition.logs_path,
            filemode="a",
            level=logging.INFO,
        )
        logger.info(node_definition.model_dump())

        try:
            function = self.functions.get(node_definition.function_name, None)
            if function is None:
                raise TierkreisError(
                    f"{self.name}: function name {node_definition.function_name} not found"
                )
            logger.info(f"running: {node_definition.function_name}")

            function(node_definition)

            node_definition.done_path.touch()
        except Exception as err:
            logger.error("encountered error: %s", err)
            with open(node_definition.error_path, "w+") as f:
                f.write(str(err))

    def write_stubs(self, stubs_path: Path) -> None:
        with open(stubs_path, "w+") as fh:
            fh.write(format_namespace(self.namespace))

    def app(self, argv: list[str]) -> None:
        if argv[1] == "--stubs-path":
            self.write_stubs(Path(argv[2]))
        else:
            self.run(Path(argv[1]))
