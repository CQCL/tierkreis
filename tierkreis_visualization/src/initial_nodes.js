const workflowId = "00000000-0000-0000-0000-000000000066";
export function parse_nodes(data) {
    let nodes = data.nodes.map((node, index) => ({
        id: node.id.toString(),
        position: {
            x: 10 + index * 50,
            y: 20 + index * 50,
        },
        data: { label: node.function_name },
    }));
    return nodes;
}

export function parse_edges(data) {
    let edges = data.edges.map((edge) => ({
        id: edge.from_node + "-" + edge.to_node,
        source: edge.from_node.toString(),
        target: edge.to_node.toString(),
        label: edge.from_port + "->" + edge.to_port,
    }));
    return edges;
}


export const initialNodes = await fetch(`http://localhost:8000/workflows/${workflowId}/nodes/-`, { method: 'GET', headers: { 'Accept': 'application/json' } })
            .then(response => response.json())
            .then(data => parse_nodes(data));
export const initialEdges = await fetch(`http://localhost:8000/workflows/${workflowId}/nodes/-`, { method: 'GET', headers: { 'Accept': 'application/json' } })
            .then(response => response.json())
            .then(data => parse_edges(data));
