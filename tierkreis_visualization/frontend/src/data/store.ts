import { create } from 'zustand';
import { addEdge, applyNodeChanges, applyEdgeChanges } from '@xyflow/react';

import { initialNodes } from '@/nodes/index';
import { initialEdges } from '@/edges/index';
import { type AppState } from '@/nodes/types';

// this is our useStore hook that we can use in our components to get parts of the store and call actions
const useStore = create<AppState>((set, get) => ({
  nodes: initialNodes,
  edges: initialEdges,
  url: "",
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
  appendNodes: (newNodes) => {
    set({
      nodes: [...get().nodes, ...newNodes],
    });
  },
  appendEdges: (newEdges) => {
    set({
      edges: [...get().edges, ...newEdges],
    });
  },
  setUrl: (url) => {
    console.log("setUrl", url);
    set({ url });
  },
  getUrl: () => {
    return get().url;
  },

}));

export default useStore;
