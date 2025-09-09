import { BackendNode } from "./types";
import { Edge } from "@xyflow/react";

export function hideChildren(
  nodeId: string,
  oldNodes: BackendNode[],
  oldEdges: Edge[]
) {
  let hidden_edges: Edge[] = [];
  oldNodes = oldNodes
    .map((node) => {
      if (node.parentId?.startsWith(nodeId)) {
        return undefined;
      }
      if (node.id === nodeId) {
        hidden_edges = node.data.hidden_edges ?? [];
        node.position = { x: 0, y: 0 };
        node.data.handles = node.data.hidden_handles ?? {
          inputs: [],
          outputs: [],
        };
        node.data.is_expanded = false;
        node.style = {
          width: 180,
          height: 130,
        };
      }
      return node;
    })
    .filter((node): node is BackendNode => node !== undefined);

  oldEdges.filter(
    (edge) =>
      edge.target.startsWith(nodeId + ":") &&
      edge.source.startsWith(nodeId + ":")
  );
  return {
    nodes: [...oldNodes],
    edges: [...oldEdges, ...hidden_edges],
  };
}
