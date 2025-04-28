// @ts-check

/**
 * Connect to an event stream. Pass in a nodes and edges list to mutate.
 * @param {JSNode[]} nodes - Event stream url to subscribe to.
 * @param {JSEdge[]} edges - Network vis library.
 * @param {string} name - List of graph edges.
 */

function createNetwork(nodes, edges, name) {
  const visnodes = new vis.DataSet(nodes);
  const visedges = new vis.DataSet(edges);

  const container = document.getElementById("mynetwork");
  const data = { nodes: visnodes, edges: visedges };
  const options = {
    layout: { hierarchical: { direction: "LR", sortMethod: "directed" } },
  };

  const network = new vis.Network(container, data, options);
  network.on("doubleClick", function (params) {
    let nodes = params.nodes;
    if (nodes.length === 1) {
      window.location.href = `${window.location.href}.${name}${nodes[0]}`;
    }
  });
  return [network, nodes, edges];
}
