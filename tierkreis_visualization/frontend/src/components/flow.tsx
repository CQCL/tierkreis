import {
  Background,
  ControlButton,
  Controls,
  Edge,
  ReactFlow,
  ReactFlowInstance
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Network } from "lucide-react";

import { SidebarTrigger } from "@/components/ui/sidebar";
import { edgeTypes } from "@/edges";
import { bottomUpLayout } from "@/graph/layoutGraph";
import { nodeTypes } from "@/nodes";
import { AppNode, BackendNode } from "@/nodes/types";

function save(newState: {
  workflowId: string;
  nodes: AppNode[];
  edges: Edge[];
}) {
  if (
    typeof window !== "undefined" &&
    newState.workflowId != "" &&
    newState.nodes.length > 0
  ) {
    window.localStorage.setItem(newState.workflowId, JSON.stringify(newState));
  }
}

export default function Flow(props: { reactFlowInstance: ReactFlowInstance<BackendNode, Edge> }) {
  const edges = props.reactFlowInstance.getEdges();
  const nodes = props.reactFlowInstance.getNodes();

  return (

  );
}
