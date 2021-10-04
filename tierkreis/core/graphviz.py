"""Visualise TierkreisGraph using graphviz."""
from typing import Iterable, Tuple
import graphviz as gv  # type: ignore

from tierkreis.core.tierkreis_graph import (
    BoxNode,
    ConstNode,
    FunctionNode,
    TierkreisGraph,
    TierkreisNode,
)


# main palettte: https://colorhunt.co/palette/343a407952b3ffc107e1e8eb
_COLOURS = {
    "background": "#E1E8EB",
    "node": "#7952B3",
    "edge": "#FFC107",
    "dark": "#343A40",
    "const": "#392656",
    "discard": "#B3525B",
}


_HTML_LABEL_TEMPLATE = """
<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="4" STYLE="ROUNDED" BGCOLOR="{node_back_color}">

{inputs_row}

    <TR>
        <TD>
            <TABLE BORDER="0" CELLBORDER="0">
                <TR>
                    <TD><FONT POINT-SIZE="11.0" FACE="Helvetica" COLOR="{label_color}">{node_label}</FONT></TD>
                </TR>
            </TABLE>
        </TD>
    </TR>

{outputs_row}

</TABLE>
"""

_HTML_PORTS_ROW_TEMPLATE = """
    <TR>
        <TD>
            <TABLE BORDER="0" CELLBORDER="0" CELLSPACING="2" CELLPADDING="2">
                <TR>
                    {port_cells}
                </TR>
            </TABLE>
        </TD>
    </TR>
"""

_HTML_PORT_TEMPLATE = (
    '<TD BGCOLOR="{back_colour}" STYLE="ROUNDED" PORT="{port}">'
    '<FONT POINT-SIZE="10.0" FACE="Helvetica" COLOR="{font_colour}">{port}</FONT></TD>'
)


def _html_ports(ports: Iterable[str]) -> str:

    return _HTML_PORTS_ROW_TEMPLATE.format(
        port_cells="".join(
            _HTML_PORT_TEMPLATE.format(
                port=port,
                back_colour=_COLOURS["edge"],
                font_colour=_COLOURS["dark"],
            )
            for port in ports
        )
    )


def _node_features(node_name: str, node: TierkreisNode) -> Tuple[str, str]:
    """Calculate node label (first) and colour (second)."""

    fillcolor = _COLOURS["node"]
    node_label = "" if node_name.startswith("NewNode") else node_name
    if isinstance(node, FunctionNode):
        f_name = node.function_name
        f_name = f_name.replace("builtin/", "")
        if node_label:
            node_label += "\n<BR/>"
        node_label += f_name
    elif isinstance(node, ConstNode):
        fillcolor = _COLOURS["const"]
        node_label += str(node.value)
    elif isinstance(node, BoxNode):
        if not node_label:
            node_label = "Box"
    elif node_name in {TierkreisGraph.input_node_name, TierkreisGraph.output_node_name}:
        # effectively only leave the ports visible
        fillcolor = _COLOURS["background"]

    return node_label, fillcolor


def tierkreis_to_graphviz(tk_graph: TierkreisGraph) -> gv.Digraph:
    """
    Return a visual representation of the TierkreisGraph as a graphviz object.

    :returns:   Representation of the TierkreisGraph
    :rtype:     graphviz.DiGraph
    """
    gv_graph = gv.Digraph(
        tk_graph.name or "Tierkreis",
        strict=False,  # stops multiple shared edges being merged
    )

    gv_graph.attr(
        rankdir="",
        ranksep="0.1",
        nodesep="0.15",
        margin="0",
        bgcolor=_COLOURS["background"],
    )

    for node_name, node in tk_graph.nodes().items():
        if node.is_discard_node():
            gv_graph.node(
                node_name,
                label="",
                shape="point",
                color=_COLOURS["discard"],
                width="0.15",
            )
            continue

        node_label, fillcolor = _node_features(node_name, node)

        in_ports = [edge.target.port for edge in tk_graph.in_edges(node_name)]
        out_ports = [edge.source.port for edge in tk_graph.out_edges(node_name)]

        # node is a table
        # first row is a single cell containing a single row table of inputs
        # second row is table containing single cell of node_label
        # third row is single cell containing a single row table of outputs

        html_label = _HTML_LABEL_TEMPLATE.format(
            node_back_color=fillcolor,
            label_color=_COLOURS["background"],
            node_label=node_label,
            inputs_row=_html_ports(in_ports) if in_ports else "",
            outputs_row=_html_ports(out_ports) if out_ports else "",
        )

        gv_graph.node(
            node_name,
            label=f"<{html_label}>",
            shape="plain",
        )

    edge_attr = {
        "penwidth": "1.5",
        "arrowhead": "none",
        "arrowsize": "0.5",
        "fontname": "Helvetica",
        "fontsize": "9",
        "color": _COLOURS["edge"],
        "fontcolor": _COLOURS["dark"],
    }

    for edge in tk_graph.edges():
        src_nodename = f"{edge.source.node_ref.name}:{edge.source.port}"
        tgt_nodename = f"{edge.target.node_ref.name}:{edge.target.port}"
        gv_graph.edge(
            src_nodename,
            tgt_nodename,
            label=str(edge.type_ or ""),
            **edge_attr,
        )
    return gv_graph


def render_graph(graph: TierkreisGraph, filename: str, format_st: str) -> None:
    """Use graphviz to render a graph visualisation to file

    :param graph: Graph to render
    :type graph: TierkreisGraph
    :param filename: Filename root to write render to
    :type filename: str
    :param format_st: Format string, e.g. "png", refer to Graphviz render
    documentation for full list.
    :type format_st: str
    """
    gv_graph = tierkreis_to_graphviz(graph)

    gv_graph.render(filename, format=format_st)
