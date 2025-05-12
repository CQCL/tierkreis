import argparse
import importlib
import json
import logging
from pathlib import Path
from typing import Callable

from tierkreis.cli.run_workflow import run_workflow
from tierkreis.controller.data.graph import GraphData
from tierkreis.exceptions import TierkreisError


def load_graph(graph_input: str) -> GraphData:
    module_name, function_name = graph_input.split(":")
    print(f"Loading graph from module '{module_name}' and function '{function_name}'")
    module = importlib.import_module(module_name, __package__)
    build_submission_graph: Callable[[], GraphData] = getattr(module, function_name)

    return build_submission_graph()


def parse_inputs(inputs: list[str]) -> dict[str, bytes]:
    parsed_inputs = {}
    for arg in inputs:
        if ":" not in arg:
            raise TierkreisError(f"Invalid argument: {arg}")
        key, value = arg.split(":")
        parsed_inputs[key] = value.encode()
    return parsed_inputs


def load_inputs(input_file: Path) -> dict[str, bytes]:
    with open(input_file, "r") as fh:
        return json.load(fh)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="tkr",
        description="Tierkreis: a workflow engine for quantum HPC.",
    )
    parser.add_argument(
        "-g",
        "--graph-location",
        required=True,
        help="Fully qualifying name of a Callable () -> GraphData. "
        + "Example: tierkreis.cli.sample_graph:simple_eval",
        type=str,
    )
    input_flags = parser.add_mutually_exclusive_group()
    input_flags.add_argument("--input-file", type=Path, help="Input as a json file.")
    input_flags.add_argument(
        "-i",
        "--input",
        nargs="+",
        help="Input as a key value list of the form -i k1:v1 k2:v2 ...",
    )

    parser.add_argument(
        "--run-id", default=None, type=int, help="Set a workflow run id"
    )
    parser.add_argument("--name", default=None, type=str, help="Set a workflow name")
    parser.add_argument(
        "-l",
        "--loglevel",
        default=logging.WARNING,
        choices=logging.getLevelNamesMapping().keys(),
        help="Set log level.",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument(
        "--registry-path", default=None, type=Path, help="Location of executable tasks."
    )
    parser.add_argument(
        "-o",
        "--print-output",
        action="store_true",
        help="Print the outputs of the top-level node. ",
    )

    # run_graph() arguments
    parser.add_argument(
        "-n",
        "--n-iterations",
        default=10**5,
        type=int,
        help="Set the maximum number of iterations.",
    )
    parser.add_argument(
        "-p",
        "--polling-interval-seconds",
        default=0.01,
        type=float,
        help="Set the controller tickrate.",
    )
    parser.add_argument(
        "-r",
        "--do-clean-restart",
        action="store_true",
        help="Clear graph files before running",
    )

    args = parser.parse_args()
    if args.verbose:
        args.log_level = logging.DEBUG

    graph = load_graph(args.graph_location)
    if args.input is not None:
        inputs = parse_inputs(args.inputs)
    elif args.input_file is not None:
        inputs = load_inputs(args.input_file)
    else:
        inputs = {}
    run_workflow(graph, inputs, **vars(args))
