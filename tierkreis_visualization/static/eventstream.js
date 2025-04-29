// @ts-check

/**
 * Connect to an event stream. Pass in a nodes and edges list to mutate.
 * @param {string} url - Event stream url to subscribe to.
 * @param {PyNode[]} nodes - List of graph nodes.
 * @param {PyEdge[]} edges - List of graph edges.
 */

function connectToStream(url, nodes, edges) {
  let eventSource = new EventSource(url);
  eventSource.onopen = (ev) => {
    console.log("opening event source");
    console.log(ev);
  };
  eventSource.addEventListener("message", (ev) => {
    const data =  /** @type {PyGraph} */ JSON.parse(ev["data"]);

    var visnodes = new vis.DataSet(data.nodes.map(createJSNode));
    var visedges = new vis.DataSet(data.edges.map(createJSEdge));

    const position = network.getViewPosition();
    const scale = network.getScale();

    network.setData({ nodes: visnodes, edges: visedges });

    console.log('hello?', data.nodes)
    // args = {
    //   position: position,
    //   scale: scale,
    //   animation: false,
    // };
    // let move = () => {
    //   network.moveTo(args);
    //   network.off("afterDrawing", move);
    // };
    // network.on("after", move);
  });
}
