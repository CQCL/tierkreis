import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Edge, getOutgoers, type NodeProps, useReactFlow } from "@xyflow/react";

import { InputHandleArray, OutputHandleArray } from "@/components/handles";
import { NodeStatusIndicator } from "@/components/StatusIndicator";
import { Button } from "@/components/ui/button";
import { URL } from "@/data/constants";
import { parseEdges, parseNodes } from "@/graph/parseGraph";
import { bottomUpLayout } from "@/graph/layoutGraph";
import { type BackendNode } from "./types";
import { Plus } from "lucide-react";

function replaceEval(
  nodeId: string,
  newNodes: BackendNode[],
  newEdges: Edge[],
  oldNodes: BackendNode[],
  oldEdges: Edge[]
) {
  // replaces an eval node with its nested subgraph
  const oldEdgesCopy: Edge[] = JSON.parse(JSON.stringify(oldEdges));
  // we only care about the last part of the id as number
  const nodesToRemove = [nodeId];
  newNodes.sort(
    (a, b) =>
      Number(a.id.substring(a.id.lastIndexOf(":"), a.id.length)) -
      Number(b.id.substring(b.id.lastIndexOf(":"), b.id.length))
  );
  oldEdgesCopy.forEach((edge) => {
    if (edge.target == nodeId) {
      if (
        edge.label === "Graph Body" &&
        getOutgoers({ id: edge.source }, oldNodes, oldEdgesCopy).length === 1
      ) {
        //Only way to identify body is by explicitly setting the label?
        nodesToRemove.push(edge.source);
      }
      // find the correct node which has an output handle of the form id:\dport_name
      let found = false;
      for (const node of newNodes) {
        if (node.id.startsWith(nodeId)) {
          node.data.handles.outputs.forEach((value) => {
            if (edge.targetHandle?.endsWith(value)) {
              node.data.handles.inputs.push(value);
              edge.targetHandle = node.id + "_" + value;
              edge.target = node.id;
              found = true;
            }
          });
          if (found) {
            break;
          }
        }
      }
      if (!found && edge.label !== "Graph Body") {
        // workaround for elements inside map, only works correctly if the unfolded value is mapped to the first input
        const node = newNodes[0];
        const value = edge.targetHandle?.split("_")[1] || "";
        node.data.handles.inputs.push(value);
        edge.targetHandle = node.id + "_" + value;
        edge.target = node.id;
      }
    }
    if (edge.source == nodeId) {
      let found = false;
      for (let index = newNodes.length - 1; index >= 0; index--) {
        const node = newNodes[index];
        if (node.id.startsWith(nodeId)) {
          node.data.handles.inputs.forEach((value) => {
            if (edge.sourceHandle?.endsWith(value) && value != "loop") {
              // != "loop" is a hack to fix loops with a single iteration TODO: check if this really works
              node.data.handles.outputs.push(value);
              edge.sourceHandle = node.id + "_" + value;
              edge.source = node.id;
              found = true;
            }
          });
          if (found) {
            break;
          }
        }
      }
      if (!found && edge.label !== "Graph Body") {
        // workaround for elements inside map, only works correctly if there is a single output
        const node = newNodes[newNodes.length - 1];
        const value = edge.sourceHandle?.split("_")[1] || "";
        node.data.handles.outputs.push(value);
        edge.sourceHandle = node.id + "_" + value;
        edge.source = node.id;
      }
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
  const tmpEdges = oldEdgesCopy.filter(
    (edge) => edge.target !== nodeId && edge.source !== nodeId
  );
  return {
    nodes: [groupNode, ...oldNodes, ...newNodes],
    edges: [...tmpEdges, ...newEdges],
  };
}

export function EvalNode({ data: node_data }: NodeProps<BackendNode>) {
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
        const nodes = parseNodes(data.nodes, data.edges, workflowId, parentId);
        const edges = parseEdges(data.edges, parentId);
        const oldEdges = reactFlowInstance.getEdges();
        const oldNodes = reactFlowInstance.getNodes();
        const { nodes: newNodes, edges: newEdges } = replaceEval(
          parentId,
          nodes,
          edges,
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
    <NodeStatusIndicator status={node_data.status}>
      <Card className="w-[180px]">
        <CardHeader>
          <CardTitle className="overflow-wrap">{node_data.title}</CardTitle>
        </CardHeader>

        <CardContent>
          <InputHandleArray
            handles={node_data.handles.inputs}
            id={node_data.id}
          />
          <OutputHandleArray
            handles={node_data.handles.outputs}
            id={node_data.id}
          />
          <div className="flex items-center justify-center">
            {node_data.status != "Not started" && (
              <Button
                variant="secondary"
                size="icon"
                onClick={() =>
                  loadChildren(
                    node_data.workflowId,
                    node_data.node_location,
                    node_data.id
                  )
                }
              >
                <Plus />
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </NodeStatusIndicator>
  );
}
