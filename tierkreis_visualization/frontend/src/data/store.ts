import { addEdge, applyEdgeChanges, applyNodeChanges } from "@xyflow/react";
import { temporal, ZundoOptions } from "zundo";
import { create } from "zustand";

import { initialEdges } from "@/edges/index";
import { initialNodes } from "@/nodes/index";
import { type AppState } from "@/nodes/types";

export type PartialState = Pick<AppState, "nodes" | "edges" | "workflowId">;
// For type annotation I pulled this out
const options: ZundoOptions<AppState, PartialState> = {
  partialize: (state: AppState): PartialState => ({
    workflowId: state.workflowId,
    nodes: state.nodes,
    edges: state.edges,
  }),
};
// this is our useStore hook that we can use in our components to get parts of the store and call actions
const useStore = create<AppState>()(
  temporal(
    (set, get) => ({
      workflowId: "",
      nodes: initialNodes,
      edges: initialEdges,
      info: { type: "Logs", content: "" },
      oldEdges: initialEdges,
      onNodesChange: (changes) => {
        set({
          nodes: applyNodeChanges(changes, get().nodes),
        });
      },
      onEdgesChange: (changes) => {
        set({
          edges: applyEdgeChanges(changes, get().edges),
        });
      },
      onConnect: (connection) => {
        set({
          edges: addEdge(connection, get().edges),
        });
      },
      setNodes: (nodes) => {
        set({ nodes });
      },
      setEdges: (edges) => {
        set({ edges });
      },
      setInfo: (info) => {
        set({ info });
      },
    }),
    options
  )
);

export default useStore;
