import {
  type Edge,
  type Node,
  type BuiltInNode,
  type OnNodesChange,
  type OnEdgesChange,
  type OnConnect,
} from "@xyflow/react";

export type PyNode = {
  id: string | number;
  status: "Not started" | "Started" | "Error" | "Finished";
  function_name: string;
  node_location: string;
};
export type BackendNode = Node<
  {
    name: string;
    status: "Started" | "Finished" | "Error" | "Not Started";
    ports: { inputs: any; outputs: any };
    handles: { inputs: any; outputs: any };
    workflowId: string;
    node_location: string;
    id: string;
    title: string;
  },
  "Input"
>;
export type AppNode = BuiltInNode | BackendNode;

export interface AppState {
  nodes: AppNode[];
  edges: Edge[];
  onNodesChange: OnNodesChange<AppNode>;
  onEdgesChange: OnEdgesChange;
  onConnect: OnConnect;
  setNodes: (nodes: AppNode[]) => void;
  setEdges: (edges: Edge[]) => void;
  replaceEval: (nodeId: string, oldNodes: AppNode[], newEdges: Edge[],) => void;
  replaceMap: (nodeId: string, oldNodes: AppNode[]) => void;
  recalculateNodePositions: () => void;
}
