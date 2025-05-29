import { PyNode } from "./types";

function nodeType(function_name: string) {
    console.log(function_name);
    switch (function_name) {
        case 'input':
            return 'input-node';
        case 'output':
            return 'output-node';
        case 'const':
            return 'const-node';
        default:
            return 'eval-node'
    }

}

export function parseNodes(data: { nodes: [PyNode] }) {
    console.log(data);
    let nodes = data.nodes.map((node, index) => ({
        id: node.id.toString(),
        position: {
            x: 10 + index * 50,
            y: 20 + index * 50,
        },
        type:  nodeType(node.function_name),
        data: {
            label: node.function_name,
            name: node.function_name,
            status: node.status,
            outputs: [
                {
                    name: "output-1",
                    value: 0,
                }]

        },
    }));
    return nodes;
}
