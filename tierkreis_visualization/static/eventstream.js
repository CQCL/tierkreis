function connectToStream(url, nodes, edges) {
  let eventSource = new EventSource(url);
  eventSource.onopen = (ev) => {
    console.log("opening event source");
    console.log(ev);
  };
  eventSource.addEventListener("message", (ev) => {
    data = JSON.parse(ev["data"]);
    for (let node in data.nodes) {
      console.log(node);
      jsNode = createJSNode(data.nodes[node]);
      console.log(jsNode);
      console.log(nodes.update);

      nodes.update(jsNode);
      network.redraw();
    }
  });
}
