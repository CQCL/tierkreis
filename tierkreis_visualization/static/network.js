// @ts-check

/**
 * Connect to an event stream. Pass in a nodes and edges list to mutate.
 * @param {PyNode[]} nodes - Event stream url to subscribe to.
 * @param {PyEdge[]} edges - Network vis library.
 * @param {string} name - List of graph edges.
 */

function createNetwork(nodes, edges, name) {
  var visnodes = new vis.DataSet(data.nodes.map(createJSNode));
  var visedges = new vis.DataSet(data.nodes.map(createJSNode));

  var container = document.getElementById("mynetwork");
  var data = { nodes: visnodes, edges: visedges };
  var options = {
    layout: { hierarchical: { direction: "LR", sortMethod: "directed" } },
  };

  var network = new vis.Network(container, data, options);
  network.on("doubleClick", function (params) {
    let nodes = params.nodes;
    if (nodes.length === 1) {
      window.location.href = `${window.location.href}.${name}${nodes[0]}`;
    }
  });
  return [network, nodes, edges];
}
