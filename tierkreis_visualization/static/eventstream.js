function connectToStream(url, nodes, edges) {
  let eventSource = new EventSource(url);
  eventSource.onopen = (ev) => {
    console.log("opening event source");
    console.log(ev);
  };
  eventSource.addEventListener("message", (ev) => {
    data = JSON.parse(ev["data"]);
    var visnodes = new vis.DataSet(data.nodes);
    var visedges = new vis.DataSet(data.edges);

    if (
      JSON.stringify(nodes) === JSON.stringify(data.nodes) &&
      JSON.stringify(edges) === JSON.stringify(data.edges)
    )
      return;

    network.setData({ nodes: visnodes, edges: visedges });
  });
}
