"""Visualise TierkreisGraph using graphviz."""
from typing import cast

from tierkreis.core.tierkreis_graph import TierkreisGraph

import graphviz as gv
from graphviz.dot import SubgraphContext  # type: ignore


def tierkreis_to_graphviz(tk_graph: TierkreisGraph) -> gv.Digraph:
    """
    Return a visual representation of the TierkreisGraph as a graphviz object.

    :returns:   Representation of the TierkreisGraph
    :rtype:     graphviz.DiGraph
    """
    gv_graph = gv.Digraph(
        "TierKreis",
        strict=True,
    )

    gv_graph.attr(rankdir="LR", ranksep="0.3", nodesep="0.15", margin="0")
    wire_color = "red"
    task_color = "darkolivegreen3"
    io_color = "green"
    out_color = "black"
    in_color = "white"

    boundary_node_attr = {"fontname": "Courier", "fontsize": "8"}
    boundary_nodes = {tk_graph.input_node_name, tk_graph.output_node_name}

    with cast(SubgraphContext, gv_graph.subgraph(name="cluster_input")) as cluster:
        cluster.attr(rank="source")
        cluster.node_attr.update(shape="point", color=io_color)
        for port in tk_graph.inputs():
            cluster.node(
                name=f"({tk_graph.input_node_name}out, {port})",
                xlabel=f"{port}",
                **boundary_node_attr,
            )

    with cast(SubgraphContext, gv_graph.subgraph(name="cluster_output")) as cluster:
        cluster.attr(rank="sink")
        cluster.node_attr.update(shape="point", color=io_color)
        for port in tk_graph.outputs():
            cluster.node(
                name=f"({tk_graph.output_node_name}in, {port})",
                xlabel=f"{port}",
                **boundary_node_attr,
            )

    node_cluster_attr = {
        "style": "rounded, filled",
        "color": task_color,
        "fontname": "Times-Roman",
        "fontsize": "10",
        "margin": "5",
        "lheight": "100",
    }
    in_port_node_attr = {
        "color": in_color,
        "shape": "point",
        "weight": "2",
        "fontname": "Helvetica",
        "fontsize": "8",
        "rank": "source",
    }
    out_port_node_attr = {
        "color": out_color,
        "shape": "point",
        "weight": "2",
        "fontname": "Helvetica",
        "fontsize": "8",
        "rank": "sink",
    }
    count = 0

    for node_name in tk_graph.nodes():

        if node_name not in boundary_nodes:
            with cast(
                SubgraphContext, gv_graph.subgraph(name=f"cluster_{node_name}{count}")
            ) as cluster:
                count = count + 1
                cluster.attr(label=node_name, **node_cluster_attr)

                incoming_edges = tk_graph.in_edges(node_name)

                for edge in incoming_edges:
                    cluster.node(
                        name=f"({node_name}in, {edge.target.port})",
                        xlabel=f"{edge.target.port}",
                        **in_port_node_attr,
                    )

                outgoing_edges = tk_graph.out_edges(node_name)

                for edge in outgoing_edges:
                    cluster.node(
                        name=f"({node_name}out, {edge.source.port})",
                        xlabel=f"{edge.source.port}",
                        **out_port_node_attr,
                    )

    edge_attr = {
        "weight": "2",
        "arrowhead": "vee",
        "arrowsize": "0.2",
        "headclip": "true",
        "tailclip": "true",
    }
    for edge in tk_graph.edges():
        src_nodename = f"({edge.source.node_ref.name}out, {edge.source.port})"
        tgt_nodename = f"({edge.target.node_ref.name}in, {edge.target.port})"

        gv_graph.edge(src_nodename, tgt_nodename, color=wire_color, **edge_attr)

    return gv_graph
