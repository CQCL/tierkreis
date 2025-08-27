from __future__ import annotations
import argparse


from tierkreis_visualization.main import start


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

    @staticmethod
    def execute(args: argparse.Namespace) -> None:
        start()
