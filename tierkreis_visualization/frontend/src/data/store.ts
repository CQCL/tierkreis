import { create } from 'zustand';
import { addEdge, applyNodeChanges, applyEdgeChanges } from '@xyflow/react';

import { initialNodes } from '@/nodes/index';
import { initialEdges } from '@/edges/index';
import { type AppState } from '@/nodes/types';
import { calculateNodePositions } from '@/graph/parseGraph';

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
    set({ url });
  },
  getUrl: () => {
    return get().url;
  },
  replaceNode: (nodeId: string) => {
    let edges = get().edges;
    const nodes = get().nodes;
    edges.forEach( (edge) => {
      if (edge.target == nodeId) {
        // todo find the correct mapping  to inputs do it in appendEdges 
        edge.target = nodeId + ":0";
      }
      if (edge.source == nodeId) {
        // map outputs to further nodes
        edge.source = "3:5";
      }
    });
     set({edges});
  },
  recalculateNodePositions: () => {
    const data = calculateNodePositions(get().nodes, get().edges);
    const newNodes = get().nodes.map((node) => ({
      ...node,
      position: data.find(position => position.id === node.id)
    }));
    set({nodes: newNodes});
    console.log(get())
  }
}));

export default useStore;
