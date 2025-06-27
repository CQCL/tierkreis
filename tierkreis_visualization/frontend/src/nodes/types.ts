import { InfoProps } from "@/components/types";
import {
  type Edge,
  type Node,
  type OnConnect,
  type OnEdgesChange,
  type OnNodesChange,
} from "@xyflow/react";

export type PyNode = {
  id: string | number;
  status: "Not started" | "Started" | "Error" | "Finished";
  function_name: string;
  node_location: string;
};
export type BackendNode = Node<{
  name: string;
  status: "Not started" | "Started" | "Error" | "Finished";
  handles: {
    inputs: string[];
    outputs: string[];
  };
  workflowId: string;
  node_location: string;
  id: string;
  title: string;
  label?: string;
}>;
export type AppNode = BackendNode;

export interface AppState {
  workflowId: string,
  nodes: AppNode[];
  edges: Edge[];
  info: InfoProps;
  oldEdges: Edge[];
  clearOldEdges: () => void;
  onNodesChange: OnNodesChange<AppNode>;
  onEdgesChange: OnEdgesChange;
  onConnect: OnConnect;
  setWorkflowId: (workflowId: string) => void;
  setNodes: (nodes: AppNode[], overwritePositions: boolean) => void;
  setEdges: (edges: Edge[]) => void;
  setInfo: (info: InfoProps) => void;
  replaceEval: (nodeId: string, oldNodes: AppNode[], newEdges: Edge[]) => void;
  replaceMap: (nodeId: string, oldNodes: AppNode[]) => void;
  recalculateNodePositions: () => void;
  tryFromStorage: (workflowId: string) => boolean;
}
