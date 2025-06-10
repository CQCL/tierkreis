import dagre from "@dagrejs/dagre";
import { AppNode, PyNode } from "@/nodes/types";
import { PyEdge } from "@/edges/types";
import { Edge } from "@xyflow/react";
import { URL } from "@/data/constants";


function nodeType(function_name: string) {
    switch (function_name) {
        case 'input':
        case 'output':
        case 'const':
        case 'ifelse':
        case 'eifelse':
            return 'default-node';
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
function getTitle(function_name: string) {
    switch (function_name) {
        case 'eifelse':
        case 'ifelse':
            return "If Else"
        default:
            return String(function_name).charAt(0).toUpperCase() + String(function_name).slice(1);
    }}

async function get_port_data(baseUrl: string, portId: string, inputs: boolean = false) {
    const type = inputs ? "/inputs/" : "/outputs/"
    const url = baseUrl + type + portId;
    const data = await fetch(url, { method: 'GET', headers: { 'Accept': 'application/json' } }).then((res) => res.json()).catch(() => { });
    return data
}

async function port_data(parentUrl: string, node_location: string) {
    const url = parentUrl.substring(0, parentUrl.lastIndexOf("/") + 1) + node_location;
    let inputs = {};
    let outputs = {}
    try {
        let res = await fetch(url, { method: 'GET', headers: { 'Accept': 'application/json' } }).then((res) => res.json());
        if (res.definition == undefined) {
            return { inputs: {}, outputs: {} }
        }
        const inputPromises = Object.entries(res.definition.inputs).map(async ([key]) => {
            const portData = await get_port_data(url, key, true);
            inputs[key] = portData;
        });
        const outputPromises = Object.entries(res.definition.outputs).map(async ([key]) => {
            const portData = await get_port_data(url, key, false);
            outputs[key] = portData;
        });

        await Promise.all([...inputPromises, ...outputPromises]);

    } catch (error) {
        console.error("Error fetching node data: ", error);
    }
    return { inputs, outputs };
}

function getHandlesFromEdges(id: Number, edges: [PyEdge]) {
    let inputs = {};
    let outputs = {};
    edges.map((edge) => {
        if (edge.from_node == id) {
            outputs[edge.from_port] = edge.from_port;
        }
        if (edge.to_node == id) {
            inputs[edge.to_port] = edge.to_port;
        }});
    let output = { inputs, outputs };
    return output;
}

export function parseNodes(nodes: [PyNode], edges: [PyEdge] ,workflowId: string, parentId?: string) {
    const url = `${URL}/${workflowId}/nodes/-`;
    return Promise.all(nodes.map((node) => {
        return port_data(url, node.node_location).then(ports => {
            return {
                id: (parentId ? `${parentId}:` : "") + node.id.toString(),
                type: nodeType(node.function_name),
                position: { x: 0, y: 0 },
                data: {
                    title: getTitle(node.function_name),
                    label: node.function_name,
                    name: node.function_name,
                    id: node.id.toString(),
                    status: node.status,
                    node_location: node.node_location,
                    workflowId: workflowId,
                    ports: ports,
                    handles: getHandlesFromEdges(Number(node.id), edges),
                },
            };
        });
    }));
}
export function parseEdges(edges: [PyEdge],parentId?: string) {
    const prefix = parentId ? `${parentId}:` : "";
    return edges.map((edge) => ({
        id: prefix + edge.from_node + "-" + prefix + edge.to_node,        
        source: prefix + edge.from_node.toString(),
        target: prefix + edge.to_node.toString(),
        sourceHandle: prefix +edge.from_node+"_"+ edge.from_port.toString(),
        targetHandle: prefix +edge.to_node+"_"+ edge.to_port.toString(),
        label: edge.from_port + "->" + edge.to_port,
    }));
}

export async function parseGraph(data: { nodes: [PyNode], edges: [PyEdge] }, workflowId: string, parentId?: string) {
    const nodes = await parseNodes(data.nodes, data.edges, workflowId, parentId);
    const edges = parseEdges(data.edges, parentId);
    console.log(edges, nodes);
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
    const nodeWidth = 350;
    const nodeHeight = 250;
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
