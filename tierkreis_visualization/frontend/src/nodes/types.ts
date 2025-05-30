import {
    type Edge,
    type Node,
    type BuiltInNode,
    type OnNodesChange,
    type OnEdgesChange,
    type OnConnect,
} from '@xyflow/react';


export type PyNode = { id: string | number; status: "Not started" | "Started" | "Error" | "Finished"; function_name: string };
export type BackendNode = Node<{ name: string, status: "Started" | "Finished" | "Error" | "Not Started", outputs: [{ name: string, value: any }], id: string }, 'Input'>;
export type AppNode = BuiltInNode | BackendNode;

export type AppState = {
    nodes: AppNode[];
    edges: Edge[];
    onNodesChange: OnNodesChange<AppNode>;
    onEdgesChange: OnEdgesChange;
    onConnect: OnConnect;
    setNodes: (nodes: AppNode[]) => void;
    setEdges: (edges: Edge[]) => void;
    appendNodes: (node: AppNode[]) => void;
    appendEdges: (edge: Edge[]) => void;
};
