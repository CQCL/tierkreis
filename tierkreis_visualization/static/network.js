function createNetwork(nodes, edges, name) {
    var visnodes = new vis.DataSet(nodes);
    var visedges = new vis.DataSet(edges);

    var container = document.getElementById("mynetwork");
    var data = { nodes: visnodes, edges: visedges };
    var options = { layout: { hierarchical: { direction: "LR", sortMethod: "directed" }}};

    var network = new vis.Network(container, data, options);
    network.on("doubleClick", function (params) {
        let nodes = params.nodes;
        if (nodes.length === 1) {
            window.location.href = `${window.location.href}.${name}${nodes[0]}`;
        }
    });
    return [network, nodes, edges]
}