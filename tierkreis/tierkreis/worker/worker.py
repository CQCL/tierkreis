import logging
from logging import getLogger
from pathlib import Path
import shutil
import subprocess
import sys
from types import TracebackType
from typing import Callable

from tierkreis.codegen import format_namespace
from tierkreis.controller.data.core import PortID
from tierkreis.controller.data.location import WorkerCallArgs
from tierkreis.controller.data.models import PModel, dict_from_pmodel
from tierkreis.controller.data.types import PType, bytes_from_ptype, ptype_from_bytes
from tierkreis.exceptions import TierkreisError
from tierkreis.namespace import Namespace, WorkerFunction
from tierkreis.worker.storage.filestorage import WorkerFileStorage
from tierkreis.worker.storage.protocol import WorkerStorage

logger = getLogger(__name__)
PrimitiveTask = Callable[[WorkerCallArgs, WorkerStorage], None]


def handle_unhandled_exception(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_traceback: TracebackType | None,
):
    logger.critical(
        "Unhandled exception", exc_info=(exc_type, exc_value, exc_traceback)
    )


class Worker:
    """A worker bundles a set of functionality under a common namespace.

    The main usage of a worker is to convert python functions into atomic tasks,
    which can then be executed by the :py:class:`tierkreis.controller.executor.uv_executor.UvExecutor`
    or similar Executors.
    From the worker type stubs can be generated to statically check the function calls.

    Example snippet for wrapping a python function:

    .. code-block:: python

        worker = Worker("numpy_worker")

        @worker.function()
        def exp(x: float, a: float) -> float:
            return value = a * np.exp(x)

    :param name: The name of the worker.
    :type name: str
    :param storage: Storage layer for the worker to interact with the ControllerStorage.
    :type storage: WorkerStorage
    """

    functions: dict[str, Callable[[WorkerCallArgs], None]]
    namespace: Namespace

    def __init__(self, name: str, storage: WorkerStorage | None = None) -> None:
        self.name = name
        self.functions = {}
        self.namespace = Namespace(name=self.name, functions={})
        if storage is None:
            self.storage: WorkerStorage = WorkerFileStorage()
        else:
            self.storage = storage
        sys.excepthook = handle_unhandled_exception

    def _load_args(
        self, f: WorkerFunction, inputs: dict[str, Path]
    ) -> dict[str, PType]:
        bs = {k: self.storage.read_input(p) for k, p in inputs.items()}
        types = self.namespace.functions[f.__name__].ins
        args = {}
        for k, b in bs.items():
            args[k] = ptype_from_bytes(b, types[k])
        return args

    def _save_results(self, outputs: dict[PortID, Path], results: PModel):
        d = dict_from_pmodel(results)
        for result_name, path in outputs.items():
            self.storage.write_output(path, bytes_from_ptype(d[result_name]))

    def primitive_task(
        self,
    ) -> Callable[[PrimitiveTask], None]:
        """Registers a python function as a primitive task with the worker."""

        def function_decorator(func: PrimitiveTask) -> None:
            def wrapper(args: WorkerCallArgs):
                func(args, self.storage)

            self.functions[func.__name__] = wrapper

        return function_decorator

    def task(self, name: str | None = None) -> Callable[[WorkerFunction], None]:
        """Registers a python function as a task with the worker."""

        def function_decorator(func: WorkerFunction) -> None:
            self.namespace.add_function(func)

            def wrapper(node_definition: WorkerCallArgs):
                kwargs = self._load_args(func, node_definition.inputs)
                results = func(**kwargs)
                self._save_results(node_definition.outputs, results)

            self.functions[func.__name__] = wrapper

        return function_decorator

    def run(self, worker_definition_path: Path) -> None:
        """Run a function with the parameters defined in worker_definition_path.

        :param worker_definition_path: The worker call args written by the controller.
        :type worker_definition_path: Path
        :raises TierkreisError: When the function execution results in an error.
        """
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

            self.storage.mark_done(node_definition.done_path)
        except Exception as err:
            logger.error("encountered error", exc_info=err)
            self.storage.write_error(node_definition.error_path, str(err))

    def write_stubs(self, stubs_path: Path) -> None:
        """Writes the type stubs to stubs_path.

        :param stubs_path: The location to write to.
        :type stubs_path: Path
        """
        with open(stubs_path, "w+") as fh:
            fh.write(format_namespace(self.namespace))

        ruff_binary = shutil.which("ruff")
        if ruff_binary:
            subprocess.run([ruff_binary, "format", stubs_path])
            subprocess.run([ruff_binary, "check", "--fix", stubs_path])
        else:
            logger.warning("No ruff binary found. Stubs will contain raw codegen.")

    def app(self, argv: list[str]) -> None:
        """Wrapper for UV execution."""
        if argv[1] == "--stubs-path":
            self.write_stubs(Path(argv[2]))
        else:
            self.run(Path(argv[1]))
