import dagre from "@dagrejs/dagre";
import { AppNode, PyNode } from "@/nodes/types";
import { PyEdge } from "@/edges/types";
import { Edge } from "@xyflow/react";



function nodeType(function_name: string) {
    switch (function_name) {
        case 'input':
            return 'input-node';
        case 'output':
            return 'output-node';
        case 'const':
            return 'const-node';
        case 'ifelse':
            return 'ifelse-node';
        case 'eifelse':
            return 'ifelse-node';
        case 'eval':
            return 'eval-node';
        case 'loop':
            return 'loop-node';
        case 'map':
            return 'map-node';
        default:
            return 'function-node'
    }

}

export function parseNodes(nodes: [PyNode], parentId?: string) {  //
    return nodes.map((node) => ({
        id: (parentId ? `${parentId}:` : "") + node.id.toString(),
        type: nodeType(node.function_name),
        position: { x: 0, y: 0 },
        data: {
            label: node.function_name,
            name: node.function_name,
            id: node.id.toString(),
            status: node.status,
            outputs: [
                {
                    name: "output-1",
                    value: 0,
                }]

        },
        //parentId: parentId ? parentId : undefined,
        //extent: parentId ? "parent" : undefined,
    }));
}
export function parseEdges(edges: [PyEdge], parentId?: string) {
    const prefix = parentId ? `${parentId}:` : "";
    return edges.map((edge) => ({
        id: prefix + edge.from_node + "-" + prefix + edge.to_node,
        source: prefix + edge.from_node.toString(),
        target: prefix + edge.to_node.toString(),
        label: edge.from_port + "->" + edge.to_port,
    }));
}

export function parseGraph(data: { nodes: [PyNode], edges: [PyEdge] }, parentId?: string) {
    const nodes = parseNodes(data.nodes, parentId);
    const edges = parseEdges(data.edges, parentId);
    const positions = calculateNodePositions(nodes, edges);
    // Update each node in nodes with a new position calculated in positions
    const updatedNodes = nodes.map((node) => ({
        ...node,
        position: positions.find(position => position.id === node.id)
    }));
    return { nodes: updatedNodes, edges };
}


export const calculateNodePositions = (
    nodes: ReturnType<typeof parseNodes> | [AppNode],
    edges: ReturnType<typeof parseEdges> | [Edge],
) => {
    //console.log(nodes);
    const nodeWidth = 350;
    const nodeHeight = 200;
    const dagreGraph = new dagre.graphlib.Graph();
    dagreGraph.setDefaultEdgeLabel(() => ({}));
    dagreGraph.setGraph({ rankdir: "TB", ranker: "longest-path" });
    nodes.forEach((node) => {
        dagreGraph.setNode(node.id, {
            width: nodeWidth,
            height: nodeHeight,
        });
    });
    edges.forEach((edge) => {
        dagreGraph.setEdge(edge.source, edge.target);
    });

    dagre.layout(dagreGraph);
    return nodes.map((node) => {
        const { x, y } = dagreGraph.node(node.id);
        return {
            id: node.id,
            x: x - nodeWidth / 2,
            y: y - nodeHeight / 2,
        };
    });
};
