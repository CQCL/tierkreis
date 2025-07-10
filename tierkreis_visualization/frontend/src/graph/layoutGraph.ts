import { CSSProperties } from "react";
import { calculateNodePositions } from "@/graph/parseGraph";
import { AppNode, BackendNode } from "@/nodes/types";
import { nodeHeight, nodeWidth } from "@/data/constants";
import { Edge } from "@xyflow/react";

interface ShallowNode {
  id: string;
  style?: CSSProperties;
  position: { x: number; y: number };
  parentId?: string;
}

export function bottomUpLayout(nodes: BackendNode[], edges: Edge[]) {
  // sort nodes by levels i.e. number of : in their id
  // calculate each level individually
  const nodeLevels = new Map<number, ShallowNode[]>();
  nodes.forEach((node) => {
    const level = node.id.split(":").length - 1;
    if (!nodeLevels.has(level)) {
      nodeLevels.set(level, []);
    }
    nodeLevels.get(level)?.push({
      id: node.id,
      style: node.style,
      position: node.position,
      parentId: node.parentId,
    });
  });
  const newNodes: AppNode[] = [];
  let previousNodes: ShallowNode[] = [];
  // construct graph from most nested level
  const levelKeys = Array.from(nodeLevels.keys()).sort((a, b) => b - a);
  for (const level of levelKeys) {
    const padding = level == 0 ? 1 : 20;
    const currentNodes = nodeLevels.get(level);
    if (!currentNodes) continue;
    const idsInLevel = new Set(currentNodes.map((nodeInfo) => nodeInfo.id));
    const levelNodes = nodes.filter((node) => idsInLevel.has(node.id));
    const levelEdges = edges.filter(
      (edge) => idsInLevel.has(edge.source) && idsInLevel.has(edge.target)
    );
    resizeNodes(levelNodes, previousNodes, 20);
    const data = calculateNodePositions(levelNodes, levelEdges, padding);
    const tmpNodes = levelNodes.map((node) => ({
      ...node,
      position: data.find((position) => position.id === node.id) || {
        id: "-",
        x: 0,
        y: 0,
      },
    }));
    newNodes.push(...tmpNodes);
    previousNodes = tmpNodes;
  }
  return newNodes.reverse();
}

function resizeNodes(
  nodesToResize: ShallowNode[],
  childNodes: ShallowNode[],
  padding: number
) {
  // resizes all the nodes in nodesToResize to fit their children
  if (!childNodes.length) return;
  for (const node of nodesToResize) {
    const children = childNodes.filter((child) => child.parentId === node.id);
    if (!children.length) continue;
    const dim = children.reduce(
      (acc, node) => {
        acc.width = Math.max(
          acc.width,
          node.position.x + (Number(node.style?.width) || nodeWidth)
        );
        acc.height = Math.max(
          acc.height,
          node.position.y + (Number(node.style?.height) || nodeHeight)
        );
        return acc;
      },
      { width: 0, height: 0 }
    );
    node.style = { width: dim.width + padding, height: dim.height + padding };
  }
}
