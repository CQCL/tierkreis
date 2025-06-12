import { create } from 'zustand';
import { addEdge, applyNodeChanges, applyEdgeChanges } from '@xyflow/react';

import { initialNodes } from '@/nodes/index';
import { initialEdges } from '@/edges/index';
import { AppNode, type AppState } from '@/nodes/types';
import { calculateNodePositions } from '@/graph/parseGraph';

// this is our useStore hook that we can use in our components to get parts of the store and call actions
const useStore = create<AppState>((set, get) => ({
  nodes: initialNodes,
  edges: initialEdges,
  workflowId: "",
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
  setWorkflowId: (workflowId) => {
    set({ workflowId });
  },
  getWorkflowId: () => {
    return get().workflowId;
  },
  replaceNode: (nodeId: string, newNodes: AppNode[]) => {
    let edges = get().edges;
    let oldNodes = get().nodes;
    let nodesToRemove = [nodeId];
    edges.forEach((edge) => {
      if (edge.target == nodeId) {
        if (edge.label === "Graph Body") {//how can we tell body 
          nodesToRemove.push(edge.source);
        }
        // find the correct node which has an output handle of the form id:\dport_name

        newNodes.sort((a, b) => a.id.localeCompare(b.id));
        let found = false;
        for (const node of newNodes) {
          if (node.id.startsWith(nodeId)) {
            Object.entries(node.data.handles.outputs).forEach(([key, value]) => {
              if (edge.targetHandle.endsWith(value)) {
                node.data.handles.inputs[key] = edge.target;
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
      }
      if (edge.source == nodeId) {
        let found = false;
        for (const node of newNodes) {
          if (node.id.startsWith(nodeId)) {
            Object.entries(node.data.handles.inputs).forEach(([key, value]) => {
              if (edge.sourceHandle.endsWith(value)) {
                node.data.handles.outputs[key] = edge.source;
                edge.sourceHandle = node.id + "_" + value;
                edge.source = node.id;
                found = true;
              }
            });
            if (found) {
              break;
            }
          }
        };
      }
    });
    oldNodes = oldNodes.filter((node) => !nodesToRemove.includes(node.id));
    set({
      nodes: [...newNodes, ...oldNodes],
      edges: edges,
    });
  },
  recalculateNodePositions: () => {
    const data = calculateNodePositions(get().nodes, get().edges);
    const newNodes = get().nodes.map((node) => ({
      ...node,
      position: data.find(position => position.id === node.id)
    }));
    set({ nodes: newNodes });
  }
}));

export default useStore;
