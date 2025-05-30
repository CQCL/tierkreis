import json
import logging
from glob import glob
from logging import getLogger
from pathlib import Path
from collections.abc import (
    Iterator,
)  # Needs to be imported from here not typing to satisfy get_origin
import sys
from typing import Callable, Iterable, ParamSpec, TypeVar, get_origin

from pydantic import BaseModel

logger = getLogger(__name__)


class WorkerCallArgs(BaseModel):
    function_name: str
    inputs: dict[str, Path]
    outputs: dict[str, Path]
    output_dir: Path
    done_path: Path
    error_path: Path
    logs_path: Path | None


Params = ParamSpec("Params")
ReturnType = TypeVar("ReturnType", bound=BaseModel)


def _load_args(inputs: dict[str, Path]) -> dict:
    kwargs = {}
    for arg_name, path in inputs.items():
        with open(path, "rb") as fh:
            value = json.loads(fh.read())

        kwargs[arg_name] = value

    return kwargs


def _save_results(outputs: dict[str, Path], results: BaseModel) -> None:
    for result_name, path in outputs.items():
        with open(path, "w+") as fh:
            fh.write(json.dumps(getattr(results, result_name)))


def _iterable_sort_key(path_str: str) -> str | int:
    v = Path(path_str).name
    try:
        return int(v)
    except ValueError:
        return v


def _load_args_iterable(
    iterable_name: str, inputs: dict[str, Path]
) -> Iterator[tuple[str, object]]:
    globbed_inputs = glob(str(inputs[iterable_name]))
    globbed_inputs.sort(key=_iterable_sort_key)
    for path in globbed_inputs:
        name = Path(path).name
        with open(path, "rb") as fh:
            yield name, json.loads(fh.read())


def _save_results_iterator(
    output_dir: Path, results: Iterable[tuple[str, object]]
) -> None:
    for k, value in results:
        with open(output_dir / k, "w+") as fh:
            fh.write(json.dumps(value))


class Worker:
    functions: dict[str, Callable[[WorkerCallArgs], None]]

    def __init__(self, name: str) -> None:
        self.name = name
        self.functions = {}

        def handle_unhandled_exception(exc_type, exc_value, exc_traceback):
            logger.critical(
                "Unhandled exception", exc_info=(exc_type, exc_value, exc_traceback)
            )

        sys.excepthook = handle_unhandled_exception

    def function(
        self,
        name: str | None = None,
    ) -> Callable[
        [
            Callable[
                ...,
                BaseModel | Iterator[tuple[str, object]],
            ]
        ],
        None,
    ]:
        """Register a function with the worker."""

        def function_decorator(
            func: Callable[
                ...,
                BaseModel | Iterator[tuple[str, object]],
            ],
        ) -> None:
            func_name = name if name is not None else func.__name__

            def wrapper(node_definition: WorkerCallArgs):
                annotations = func.__annotations__
                annotations.pop("return")
                # If there is only one argument and its value is iterator,
                # we need to load multiple files to the iterator.
                if (
                    len(annotations) == 1
                    and get_origin(next(iter(annotations.values()))) is Iterator
                ):
                    input_iterator_name, _ = annotations.popitem()
                    iterator = _load_args_iterable(
                        input_iterator_name, node_definition.inputs
                    )
                    results = func(iterator)
                else:
                    kwargs = _load_args(node_definition.inputs)
                    results = func(**kwargs)

                if isinstance(results, Iterator):
                    _save_results_iterator(node_definition.output_dir, results)
                else:
                    _save_results(node_definition.outputs, results)

            self.functions[func_name] = wrapper

        return function_decorator

    def run(self, worker_definition_path: Path) -> None:
        """Run a function."""
        with open(worker_definition_path, "r") as fh:
            node_definition = WorkerCallArgs(**json.loads(fh.read()))

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
                raise ValueError(
                    f"{self.name}: function name {node_definition.function_name} not found"
                )
            logger.info(f"running: {node_definition.function_name}")

            function(node_definition)

            node_definition.done_path.touch()
        except Exception as err:
            logger.error("encountered error: %s", err)
            with open(node_definition.error_path, "w+") as f:
                f.write(str(err))
