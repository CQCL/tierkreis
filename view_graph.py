#!/usr/bin/env python3

from typing import BinaryIO
import click
from tierkreis.core.tierkreis_graph import TierkreisGraph
from tierkreis.core.graphviz import tierkreis_to_graphviz
import tierkreis.core.protos.tierkreis.graph as pg


@click.command()
@click.argument("proto_file", type=click.File("rb"))
@click.argument("out", type=click.Path(exists=False))
@click.option(
    "--fmt",
    default="pdf",
    help="Output format (as available from graphviz). Default=pdf",
)
def render(proto_file: BinaryIO, out: str, fmt: str):
    proto = pg.Graph().parse(proto_file.read())

    tk_g = TierkreisGraph.from_proto(proto)

    gv = tierkreis_to_graphviz(tk_g)
    gv.render(filename=out + ".gv", format=fmt, view=True)


if __name__ == "__main__":
    render()
