#!/usr/bin/env python3

import argparse
from pathlib import Path
from tierkreis.core.tierkreis_graph import TierkreisGraph
from tierkreis.core.graphviz import tierkreis_to_graphviz
import tierkreis.core.protos.tierkreis.graph as pg


parser = argparse.ArgumentParser(
    description="Render a graphviz from protobuf of Tierkreis Graph."
)
parser.add_argument(
    "proto_file", metavar="proto_file", type=str, help="Input proto file."
)
parser.add_argument("out", metavar="out", type=str, help="Out file name.")
parser.add_argument(
    "--fmt",
    metavar="fmt",
    type=str,
    help="Output format (as available from graphviz). Default=pdf",
    default="pdf",
)


args = parser.parse_args()

with open(Path(args.proto_file), "rb") as f:
    proto = pg.Graph().parse(f.read())

tk_g = TierkreisGraph.from_proto(proto)

gv = tierkreis_to_graphviz(tk_g)
gv.render(filename=args.out + ".gv", format=args.fmt, view=True)
