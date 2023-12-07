"""Visualise TierkreisGraph using graphviz."""
import textwrap
from typing import Iterable, NewType, Optional, Tuple, cast

import graphviz as gv

from tierkreis.core.tierkreis_graph import (
    BoxNode,
    ConstNode,
    FunctionNode,
    GraphValue,
    InputNode,
    Location,
    MatchNode,
    OutputNode,
    TagNode,
    TierkreisGraph,
    TierkreisNode,
)

# old palettte: https://colorhunt.co/palette/343a407952b3ffc107e1e8eb
# _COLOURS = {
#     "background": "white",
#     "node": "#7952B3",
#     "edge": "#FFC107",
#     "dark": "#343A40",
#     "const": "#7c55b4",
#     "discard": "#ff8888",
#     "node_border": "#9d80c7",
#     "port_border": "#ffd966",
# }

# ZX colours
# _COLOURS = {
#     "background": "white",
#     "node": "#629DD1",
#     "edge": "#297FD5",
#     "dark": "#112D4E",
#     "const": "#a1eea1",
#     "discard": "#ff8888",
#     "node_border": "#D8F8D8",
#     "port_border": "#E8A5A5",
# }

# Conference talk colours
_COLOURS = {
    "background": "white",
    "node": "#ACCBF9",
    "edge": "#1CADE4",
    "dark": "black",
    "const": "#77CEEF",
    "discard": "#ff8888",
    "node_border": "white",
    "port_border": "#1CADE4",
}


_FONTFACE = "monospace"

_HTML_LABEL_TEMPLATE = """
<TABLE BORDER="{border_width}" CELLBORDER="0" CELLSPACING="1" CELLPADDING="1" BGCOLOR="{node_back_color}" COLOR="{border_colour}">

{inputs_row}

    <TR>
        <TD>
            <TABLE BORDER="0" CELLBORDER="0">
                <TR>
                    <TD><FONT POINT-SIZE="{fontsize}" FACE="{fontface}" COLOR="{label_color}"><B>{node_label}</B></FONT></TD>
                </TR>
            </TABLE>
        </TD>
    </TR>

{outputs_row}

</TABLE>
"""


def _format_html_label(**kwargs):
    _HTML_LABEL_DEFAULTS = {
        "label_color": _COLOURS["dark"],
        "node_back_color": _COLOURS["node"],
        "inputs_row": "",
        "outputs_row": "",
        "border_colour": _COLOURS["port_border"],
        "border_width": "1",
        "fontface": _FONTFACE,
        "fontsize": 11.0,
    }
    return _HTML_LABEL_TEMPLATE.format(**{**_HTML_LABEL_DEFAULTS, **kwargs})


_HTML_PORTS_ROW_TEMPLATE = """
    <TR>
        <TD>
            <TABLE BORDER="0" CELLBORDER="0" CELLSPACING="3" CELLPADDING="2">
                <TR>
                    {port_cells}
                </TR>
            </TABLE>
        </TD>
    </TR>
"""

_HTML_PORT_TEMPLATE = (
    '<TD BGCOLOR="{back_colour}" COLOR="{border_colour}"'
    ' PORT="{port_id}" BORDER="{border_width}">'
    '<FONT POINT-SIZE="10.0" FACE="{fontface}" COLOR="{font_colour}">{port}</FONT></TD>'
)

_INPUT_PREFIX = "in."
_OUTPUT_PREFIX = "out."


def _html_ports(ports: Iterable[str], id_prefix: str) -> str:
    return _HTML_PORTS_ROW_TEMPLATE.format(
        port_cells="".join(
            _HTML_PORT_TEMPLATE.format(
                port=port,
                # differentiate input and output node identifiers
                # with a prefix
                port_id=id_prefix + port,
                back_colour=_COLOURS["background"],
                font_colour=_COLOURS["dark"],
                border_width="1",
                border_colour=_COLOURS["port_border"],
                fontface=_FONTFACE,
            )
            for port in ports
        )
    )


def _trim_str(instr: str, max_len: int = 10) -> str:
    return textwrap.shorten(instr, width=max_len, placeholder="...")


def _thunk_name(thunk: TierkreisGraph) -> str:
    name = "thunk"
    if thunk.name:
        name += f"\n<BR/><I>{thunk.name}</I>"

    return name


def _print_location(loc: Location) -> str:
    if loc.location == []:
        return ""
    return "@" + "/".join(loc.location)


def _node_id(prefix: str, idx: int, sep: str = "//") -> str:
    return f"{prefix}{sep}{idx}"


def _node_features(node: TierkreisNode) -> Tuple[str, str]:
    """Calculate node label (first) and colour (second)."""

    fillcolor = _COLOURS["node"]
    if isinstance(node, FunctionNode):
        f_name = node.function_name
        node_label = str(f_name)
    elif isinstance(node, ConstNode):
        fillcolor = _COLOURS["const"]
        value = node.value
        if isinstance(value, GraphValue):
            fillcolor = _COLOURS["edge"]
            node_label = _thunk_name(value.value)
        else:
            const_str = node.value.viz_str()
            node_label = _trim_str(const_str, 15)
    elif isinstance(node, MatchNode):
        node_label = "Match"
    elif isinstance(node, TagNode):
        node_label = "Tag: " + node.tag_name
    elif isinstance(node, BoxNode):
        node_label = f"Box{_print_location(node.location)}"
        name = cast(BoxNode, node).graph.name
        if name:
            node_label += f": {name}"
    elif isinstance(node, (InputNode, OutputNode)):
        # effectively only leave the ports visible
        fillcolor = _COLOURS["background"]
        node_label = " "
    else:
        node_label = ""

    return node_label, fillcolor


def tierkreis_to_graphviz(
    tk_graph: TierkreisGraph,
    initial_graph: Optional[gv.Digraph] = None,
    prefix: str = "",
    unbox_level: int = 0,
    merge_copies: bool = True,
    unbox_graph_names: Optional[set[str]] = None,
) -> gv.Digraph:
    """
    Return a visual representation of the TierkreisGraph as a graphviz object.

    :returns:   Representation of the TierkreisGraph
    :rtype:     graphviz.DiGraph
    """
    if merge_copies:
        tk_graph = _merge_copies(tk_graph)
    gv_graph = (
        gv.Digraph(
            tk_graph.name or "Tierkreis",
            strict=False,  # stops multiple shared edges being merged
        )
        if initial_graph is None
        else initial_graph
    )
    graph_atrr = {
        "rankdir": "",
        "ranksep": "0.1",
        "nodesep": "0.15",
        "margin": "0",
        "bgcolor": _COLOURS["background"],
    }
    if tk_graph.name:
        graph_label = _format_html_label(
            node_label=tk_graph.name,
            fontsize=11.0,
            border_width=2.0,
            node_back_color=_COLOURS["background"],
        )
        graph_atrr["label"] = f"<{graph_label}>"
        graph_atrr["labelloc"] = "t"
    gv_graph.attr(**graph_atrr)

    unboxed_nodes = set()
    unthunked_nodes = set()
    discard_nodes = set()
    copy_nodes = set()
    no_outport_nodes = set()
    for node_idx, node in enumerate(tk_graph.nodes()):
        node_identifier = _node_id(prefix, node_idx)
        if node.is_discard_node():
            gv_graph.node(
                node_identifier,
                label="",
                shape="point",
                color=_COLOURS["discard"],
                width="0.1",
            )
            discard_nodes.add(node_identifier)
            continue
        if node.is_copy_node():
            gv_graph.node(
                node_identifier,
                label="",
                shape="point",
                color=_COLOURS["edge"],
                width="0.1",
            )
            copy_nodes.add(node_identifier)
            continue

        node_label, fillcolor = _node_features(node)

        # node is a table
        # first row is a single cell containing a single row table of inputs
        # second row is table containing single cell of node_label
        # third row is single cell containing a single row table of outputs

        in_ports = [edge.target.port for edge in tk_graph.in_edges(node_idx)]
        out_ports = [edge.source.port for edge in tk_graph.out_edges(node_idx)]
        subgraph = None
        isbox = False
        isgraphconst = False
        if isinstance(node, BoxNode):
            isbox = True
            subgraph = node.graph
        if isinstance(node, ConstNode):
            val = node.value
            if isinstance(val, GraphValue):
                subgraph = val.value
                isgraphconst = True
        if (
            unbox_level > 0
            and subgraph is not None
            and (not unbox_graph_names or subgraph.name in unbox_graph_names)
        ):
            cluster_name = "cluster" + node_identifier
            if isbox:
                unboxed_nodes.add(node_identifier)
                subgraph = cast(BoxNode, node).graph
                out_ports = []
            else:
                unthunked_nodes.add(node_identifier)
                subgraph = cast(GraphValue, cast(ConstNode, node).value).value

            ctx_mgr = gv_graph.subgraph(name=cluster_name)
            assert ctx_mgr is not None
            with ctx_mgr as c:
                tierkreis_to_graphviz(
                    subgraph,
                    initial_graph=c,
                    prefix=node_identifier,
                    unbox_level=unbox_level - 1,
                )

                if isgraphconst:
                    html_label = _format_html_label(
                        node_back_color=_COLOURS["edge"],
                        node_label=_thunk_name(subgraph),
                        border_colour=_COLOURS["port_border"],
                    )
                    c.node(
                        node_identifier + "thunk",
                        shape="plain",
                        label=f"<{html_label}>",
                    )
                    c.attr(label="")
                else:
                    html_label = _format_html_label(
                        node_back_color=fillcolor,
                        border_colour=_COLOURS["node_border"],
                        node_label=(node_label) if isbox else "Thunk",
                        outputs_row=_html_ports(out_ports, _OUTPUT_PREFIX)
                        if out_ports
                        else "",
                    )
                    c.attr(label=f"<{html_label}>")
                c.attr(
                    margin="10",
                    style="dashed",
                    color=(_COLOURS["const"], _COLOURS["edge"])[unbox_level % 2],
                )
            continue

        if isinstance(node, ConstNode):
            # unnecessary "value" port for constants
            no_outport_nodes.add(node_identifier)
            out_ports = []

        html_label = _format_html_label(
            node_back_color=fillcolor,
            node_label=node_label,
            inputs_row=_html_ports(in_ports, _INPUT_PREFIX) if in_ports else "",
            outputs_row=_html_ports(out_ports, _OUTPUT_PREFIX) if out_ports else "",
            border_colour=_COLOURS["background"]
            if fillcolor == _COLOURS["background"]
            else _COLOURS["node_border"],
        )
        gv_graph.node(
            node_identifier,
            label=f"<{html_label}>",
            shape="plain",
        )

    edge_attr = {
        "penwidth": "1.5",
        "arrowhead": "none",
        "arrowsize": "1.0",
        "fontname": _FONTFACE,
        "fontsize": "9",
        "color": _COLOURS["edge"],
        "fontcolor": "black",
    }
    for edge in tk_graph.edges():
        src_node = _node_id(prefix, edge.source.node_ref.idx)
        tgt_node = _node_id(prefix, edge.target.node_ref.idx)

        if src_node in unboxed_nodes:
            src_node = _node_id(src_node, TierkreisGraph.output_node_idx)
            # box output node only has input ports
            outport_str = (
                ""
                if src_node in no_outport_nodes
                else f":{_INPUT_PREFIX}{edge.source.port}"
            )
            src_nodeport = f"{src_node}{outport_str}"
        elif src_node in unthunked_nodes:
            src_nodeport = src_node + "thunk"
        elif src_node in copy_nodes:
            src_nodeport = src_node
        else:
            outport_str = (
                ""
                if src_node in no_outport_nodes
                else f":{_OUTPUT_PREFIX}{edge.source.port}"
            )
            src_nodeport = f"{src_node}{outport_str}"

        if tgt_node in unboxed_nodes:
            tgt_node = _node_id(tgt_node, TierkreisGraph.input_node_idx)
            # box input node only has output ports
            tgt_nodeport = f"{tgt_node}:{_OUTPUT_PREFIX}{edge.target.port}"
        elif tgt_node in discard_nodes or tgt_node in copy_nodes:
            # discard/copy nodes don't have ports (not HTML labels)
            tgt_nodeport = tgt_node
        else:
            tgt_nodeport = f"{tgt_node}:{_INPUT_PREFIX}{edge.target.port}"

        if src_node in copy_nodes or edge.type_ is None:
            # copy edge output types can be seen from the input
            edge_label = ""
        else:
            edge_label = textwrap.fill(
                str(edge.type_), 20, fix_sentence_endings=True, break_long_words=False
            )
        gv_graph.edge(
            src_nodeport,
            tgt_nodeport,
            label=edge_label,
            **edge_attr,
        )

    return gv_graph


def render_graph(
    graph: TierkreisGraph, filename: str, format_st: str, **kwargs
) -> None:
    """Use graphviz to render a graph visualisation to file

    :param graph: Graph to render
    :type graph: TierkreisGraph
    :param filename: Filename root to write render to
    :type filename: str
    :param format_st: Format string, e.g. "png", refer to Graphviz render
    documentation for full list.
    :type format_st: str
    """
    gv_graph = tierkreis_to_graphviz(graph, **kwargs)

    gv_graph.render(filename, format=format_st)


# Merging copies produces invalid graphs
_CopyMergedGraph = NewType("_CopyMergedGraph", TierkreisGraph)


def _merge_copies(g: TierkreisGraph) -> _CopyMergedGraph:
    """Merge adjacent copy nodes - adds extra ports to copy nodes so won't pass
    type check."""
    candidates = {idx for idx, node in enumerate(g.nodes()) if node.is_copy_node()}
    while candidates:
        node_name = candidates.pop()
        copy_children = (
            n.idx
            for e in g.out_edges(node_name)
            if g[(n := e.target.node_ref)].is_copy_node()
        )

        if (copy_child := next(copy_children, None)) is None:
            continue

        # this node is going to merge with child - check it again
        candidates.add(node_name)

        eds = list(g.out_edges(copy_child))

        # remove child and all connected edges
        g._graph.remove_node(copy_child)
        # remove from candidates if still a candidate
        if copy_child in candidates:
            candidates.remove(copy_child)

        for e in eds:
            # source port is not valid - this graph will not type check
            g._graph.add_edge(
                node_name, e.target.node_ref.idx, ("", e.target.port), type=e.type_
            )

    return _CopyMergedGraph(g)
