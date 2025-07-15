import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Edge, useReactFlow, type NodeProps } from "@xyflow/react";

import { InputHandleArray, OutputHandleArray } from "@/components/handles";
import { NodeStatusIndicator } from "@/components/StatusIndicator";
import { Button } from "@/components/ui/button";
import { URL } from "@/data/constants";
import { parseNodes } from "@/graph/parseGraph";
import { type BackendNode } from "@/nodes/types";
import { Plus } from "lucide-react";
import { bottomUpLayout } from "@/graph/layoutGraph";

function replaceMap(
  nodeId: string,
  newNodes: BackendNode[],
  oldNodes: BackendNode[],
  oldEdges: Edge[]
) {
  // copy over all the inputs and outputs from the map node to its children
  let edges: Edge[] = JSON.parse(JSON.stringify(oldEdges));
  const nodesToRemove = [nodeId];
  const edgesToRemove: string[] = [];
  const newEdges: Edge[] = [];
  edges.forEach((edge) => {
    if (edge.target == nodeId) {
      edgesToRemove.push(edge.id);
      newNodes.forEach((node) => {
        if (typeof edge.targetHandle === "string") {
          node.data.handles.inputs.push(
            edge.targetHandle.replace(`${nodeId}_`, "")
          );
        }
        const newEdge = {
          ...edge,
          target: node.id,
          targetHandle:
            node.id + "_" + edge.targetHandle?.replace(`${nodeId}_`, ""),
          id: edge.id.replace(`${nodeId}`, `${node.id}`),
        };
        newEdges.push(newEdge);
      });
    }
    if (edge.source == nodeId) {
      edgesToRemove.push(edge.id);
      newNodes.forEach((node) => {
        if (typeof edge.sourceHandle === "string") {
          node.data.handles.outputs.push(
            edge.sourceHandle.replace(`${nodeId}_`, "")
          );
        }
        const newEdge = {
          ...edge,
          source: node.id,
          sourceHandle:
            node.id + "_" + edge.sourceHandle?.replace(`${nodeId}_`, ""),
          id: edge.id.replace(`${nodeId}`, `${node.id}`),
        };
        newEdges.push(newEdge);
      });
    }
  });
  const groupNode = {
    id: nodeId,
    type: "group",
    position: { x: 0, y: 0 },
    data: {},
    parentId: oldNodes.find((node) => node.id === nodeId)?.parentId,
  } as BackendNode;
  oldNodes = oldNodes.filter((node) => !nodesToRemove.includes(node.id));
  edges = edges.filter((edge) => !edgesToRemove.includes(edge.id));
  // there are no edges between the newNodes
  return {
    nodes: [groupNode, ...oldNodes, ...newNodes],
    edges: [...edges, ...newEdges],
  };
}

export function MapNode({ data }: NodeProps<BackendNode>) {
  const reactFlowInstance = useReactFlow<BackendNode, Edge>();
  const loadChildren = async (
    workflowId: string,
    node_location: string,
    parentId: string
  ) => {
    const url = `${URL}/${workflowId}/nodes/${node_location}`;
    fetch(url, { method: "GET", headers: { Accept: "application/json" } })
      .then((response) => response.json())
      .then((data) => {
        const nodes = parseNodes(
          data.nodes,
          data.edges,
          workflowId,
          data.setInfo,
          parentId
        );
        const oldEdges = reactFlowInstance.getEdges();
        const oldNodes = reactFlowInstance.getNodes();
        const { nodes: newNodes, edges: newEdges } = replaceMap(
          parentId,
          nodes,
          oldNodes,
          oldEdges
        );
        const positionedNodes = bottomUpLayout(newNodes, [
          ...newEdges,
          ...oldEdges,
        ]);
        reactFlowInstance.setNodes(positionedNodes);
        reactFlowInstance.setEdges(newEdges);
      });
  };
  return (
    <NodeStatusIndicator status={data.status}>
      <Card className="w-[180px]">
        <CardHeader>
          <CardTitle>{data.title}</CardTitle>
        </CardHeader>

        <CardContent>
          <div className="flex items-center justify-center">
            <Button
              variant="secondary"
              size="icon"
              onClick={() =>
                loadChildren(data.workflowId, data.node_location, data.id)
              }
            >
              <Plus />
            </Button>
          </div>
          <InputHandleArray handles={data.handles.inputs} id={data.id} />
          <OutputHandleArray handles={data.handles.outputs} id={data.id} />
        </CardContent>
      </Card>
    </NodeStatusIndicator>
  );
}
