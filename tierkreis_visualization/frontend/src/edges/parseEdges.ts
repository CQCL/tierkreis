export function parseEdges(data, parentId?: string) {
    const prefix = parentId ? `${parentId}:` : "";
    let edges = data.edges.map((edge) => ({
        id: prefix + edge.from_node + "-" + prefix + edge.to_node,
        source: prefix + edge.from_node.toString(),
        target: prefix + edge.to_node.toString(),
        label: edge.from_port + "->" + edge.to_port,
    }));
    return edges;
}
