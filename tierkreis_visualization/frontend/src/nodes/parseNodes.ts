export function parseNodes(data) {
    console.log(data);
    let nodes = data.nodes.map((node, index) => ({
        id: node.id.toString(),
        position: {
            x: 10 + index * 50,
            y: 20 + index * 50,
        },
        type: "input-node",
        data: {
            label: node.function_name,
            name: "node-name",
            color: "#000000",
            outputs: [
                {
                    name: "output-1",
                    value: 0,
                }]

        },
    }));
    return nodes;
}
