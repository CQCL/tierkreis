from __future__ import annotations
import argparse
import os
from pathlib import Path

from tierkreis.builder import GraphBuilder
from watchfiles import PythonFilter, run_process

from tierkreis.cli.tkr import load_graph
from tierkreis_visualization.main import start, visualize_graph


def _vizualize_from_location(graph_location: str) -> None:
    graph = load_graph(graph_location)
    if isinstance(graph, GraphBuilder):
        visualize_graph(graph.get_data())
    else:
        visualize_graph(graph)


class TierkreisVizCli:
    @staticmethod
    def add_subcommand(
        main_parser: argparse._SubParsersAction[argparse.ArgumentParser],
    ) -> None:
        parser: argparse.ArgumentParser = main_parser.add_parser(
            "viz",
            description="Runs the tierkreis visualization.",
        )
        parser.set_defaults(func=TierkreisVizCli.execute)

        dev_parser = main_parser.add_parser(
            "dev", description="Inspect a graph without running it"
        )
        dev_parser.add_argument(
            "-g",
            "--graph-location",
            help="Fully qualifying name of a Callable () -> GraphBuilder. "
            + "Example: tierkreis.cli.sample_graph:simple_eval"
            + "Or a path to a python file and function."
            + "Example: examples/hello_world/hello_world_graph.py:hello_graph",
            type=str,
            required=True,
        )
        dev_parser.set_defaults(func=TierkreisVizCli.dev)

    @staticmethod
    def execute(args: argparse.Namespace) -> None:
        start()

    @staticmethod
    def dev(args: argparse.Namespace) -> None:
        module_name, _function_name = args.graph_location.split(":")
        # By default watch the directory with the graph definition in for changes.
        #
        # This might be suboptimal when changes happen in e.g. the virtual env
        # but this is reasonably similar to how fastapi dev server works.
        if ".py" not in module_name:
            path = Path(os.getcwd()).parent
        else:
            path = Path(module_name).parent
        print(f"Listening for changes at {path}")
        run_process(
            path,
            target=_vizualize_from_location,
            args=(args.graph_location,),
            watch_filter=PythonFilter(),
            recursive=True,
        )
