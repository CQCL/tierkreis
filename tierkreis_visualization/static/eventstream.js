function connectToStream(url, nodes, edges) {
  let eventSource = new EventSource(url);
  eventSource.onopen = (ev) => {
    console.log("opening event source");
    console.log(ev);
  };
  eventSource.addEventListener("message", (ev) => {
    data = JSON.parse(ev["data"]);
    const visnodes = new vis.DataSet(data.nodes.map(createJSNode));
    const visedges = new vis.DataSet(data.edges.map(createJSEdge));

    position = network.getViewPosition();
    scale = network.getScale();

    network.setData({ nodes: visnodes, edges: visedges });
    args = {
      position: position,
      scale: scale,
      animation: false,
    };
    let move = () => {
      network.moveTo(args);
      network.off("afterDrawing", move);
    };
    network.on("afterDrawing", move);
  });
}
