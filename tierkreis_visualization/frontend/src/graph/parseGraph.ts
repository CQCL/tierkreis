import { PyEdge } from "@/edges/types";
import { AppNode, PyNode } from "@/nodes/types";
import dagre from "@dagrejs/dagre";
import { Edge } from "@xyflow/react";
import { nodeHeight, nodeWidth } from "@/data/constants";
import { CSSProperties } from "react";
import { InfoProps } from "@/components/types";

function nodeType(function_name: string) {
  if (function_name.match(/^L?\d+$/)) {
    return "eval-node";
  }
  switch (function_name) {
    case "input":
    case "output":
    case "const":
    case "ifelse":
    case "eifelse":
      return "default-node";
    case "eval":
    case "loop":
      return "eval-node";
    case "map":
      return "map-node";
    default:
      return "default-node";
  }
}
function getTitle(function_name: string) {
  if (function_name.match(/^L\d+$/)) {
    return "Loop Iteration";
  }
  if (function_name.match(/^\d+$/)) {
    return "Map Value";
  }
  switch (function_name) {
    case "eifelse":
    case "ifelse":
      return "If Else";
    case "input":
    case "output":
    case "const":
    case "eval":
    case "loop":
    case "map":
      return (
        String(function_name).charAt(0).toUpperCase() +
        String(function_name).slice(1)
      );
    default:
      return "Function";
  }
}

function getHandlesFromEdges(id: number, edges: PyEdge[]) {
  const inputs: string[] = [];
  const outputs: string[] = [];
  edges.map((edge) => {
    if (edge.from_node == id) {
      outputs.push(edge.from_port);
    }
    if (edge.to_node == id) {
      inputs.push(edge.to_port);
    }
  });
  return { inputs, outputs };
}

export function parseNodes(
  nodes: PyNode[],
  edges: PyEdge[],
  workflowId: string,
  setInfo: (arg: InfoProps) => void,
  parentId?: string
): AppNode[] {
  // child nodes prepend their parents id eg. [0,1,2] => [0:0,0:1,0:2]
  const parsedNodes = nodes.map((node) => ({
    id: (parentId ? `${parentId}:` : "") + node.id.toString(),
    type: nodeType(node.function_name),
    position: { x: 0, y: 0 },
    data: {
      name: node.function_name,
      status: node.status,
      handles: getHandlesFromEdges(Number(node.id), edges),
      workflowId: workflowId,
      node_location: node.node_location,
      title: getTitle(node.function_name),
      id: (parentId ? `${parentId}:` : "") + node.id.toString(),
      label: node.function_name,
      setInfo: setInfo,
      pinned: false,
    },
    parentId: parentId ? `${parentId}` : undefined,
  }));
  return parsedNodes;
}

function replacer(_: string, value: unknown): unknown {
  if (value === null || value === undefined) {
    return;
  }
  if (typeof value === "number") {
    const highThreshold = 1_000;
    const lowThreshold = 0.0001;
    if (
      Math.abs(value) >= highThreshold ||
      (Math.abs(value) < lowThreshold && value !== 0)
    ) {
      return value.toExponential(); // Convert it to scientific notation
    }
    return Number(value.toPrecision(3));
  }
  return value;
}

export function parseEdges(edges: PyEdge[], parentId?: string): Edge[] {
  const uniqueCount: Map<string, number> = new Map();
  const prefix = parentId ? `${parentId}:` : "";
  return edges.map((edge) => {
    const id = prefix + edge.from_node + "-" + prefix + edge.to_node;
    const count = uniqueCount.get(id) || 0;
    uniqueCount.set(id, count + 1);
    return {
      type: "custom-edge",
      id:
        prefix +
        edge.from_node +
        "-" +
        count.toString() +
        "-" +
        prefix +
        edge.to_node,
      source: prefix + edge.from_node.toString(),
      target: prefix + edge.to_node.toString(),
      sourceHandle: prefix + edge.from_node + "_" + edge.from_port,
      targetHandle: prefix + edge.to_node + "_" + edge.to_port,
      label:
        edge.to_port == "body"
          ? "Graph Body"
          : JSON.stringify(edge.value, replacer, 2),
    };
  });
}

export function parseGraph(
  data: { nodes: PyNode[]; edges: PyEdge[] },
  workflowId: string,
  setInfo: (arg: InfoProps) => void,
  parentId?: string
) {
  const nodes = parseNodes(
    data.nodes,
    data.edges,
    workflowId,
    setInfo,
    parentId
  );
  const edges = parseEdges(data.edges, parentId);
  return { nodes, edges };
}

export const calculateNodePositions = (
  nodes: { id: string; style?: CSSProperties }[],
  edges: Edge[],
  padding: number = 0
) => {
  const dagreGraph = new dagre.graphlib.Graph();
  const nodeIds = new Set(nodes.map((node) => node.id));
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  dagreGraph.setGraph({ rankdir: "TB", ranker: "longest-path" });
  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, {
      width: node.style?.width ? Number(node.style.width) : nodeWidth,
      height: node.style?.height ? Number(node.style.height) : nodeHeight,
    });
  });
  edges.forEach((edge) => {
    if (nodeIds.has(edge.source) && nodeIds.has(edge.target))
      dagreGraph.setEdge(edge.source, edge.target);
  });
  dagre.layout(dagreGraph);
  return nodes.map((node) => {
    const { x, y, width, height } = dagreGraph.node(node.id);
    return {
      id: node.id,
      x: x - width / 2 + padding,
      y: y - height / 2 + padding,
    };
  });
};
