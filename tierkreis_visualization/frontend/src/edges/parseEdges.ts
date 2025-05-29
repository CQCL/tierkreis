export function parseEdges(data) {
    let edges = data.edges.map((edge) => ({
        id: edge.from_node + "-" + edge.to_node,
        source: edge.from_node.toString(),
        target: edge.to_node.toString(),
        label: edge.from_port + "->" + edge.to_port,
    }));
    return edges;
}
