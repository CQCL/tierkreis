import { create } from "zustand";
import { temporal } from "zundo";
import { addEdge, applyNodeChanges, applyEdgeChanges } from "@xyflow/react";

import { initialNodes } from "@/nodes/index";
import { initialEdges } from "@/edges/index";
import { AppNode, type AppState } from "@/nodes/types";
import { Edge } from "@xyflow/react";
import { calculateNodePositions } from "@/graph/parseGraph";

// this is our useStore hook that we can use in our components to get parts of the store and call actions
const useStore = create<AppState>()(
  temporal(
    (set, get) => ({
      nodes: initialNodes,
      edges: initialEdges,
      onNodesChange: (changes) => {
        set({
          nodes: applyNodeChanges(changes, get().nodes),
        });
      },
      onEdgesChange: (changes) => {
        console.log("calling on edges change");
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

      //todo use getIncomers and getOutcomers
      replaceEval: (
        nodeId: string,
        newNodes: AppNode[],
        newEdges: Edge[],
      ) => {
        const edges: Edge[] = JSON.parse(JSON.stringify(get().edges)); // is there a better way to do this?
        let oldNodes = get().nodes;
        const nodesToRemove = [nodeId];
        newNodes.sort((a, b) => a.id.localeCompare(b.id));
        edges.forEach((edge) => {
          if (edge.target == nodeId) {
            if (edge.label === "Graph Body") {
              //how can we tell body
              nodesToRemove.push(edge.source);
            }
            // find the correct node which has an output handle of the form id:\dport_name
            let found = false;
            for (const node of newNodes) {
              if (node.id.startsWith(nodeId)) {
                Object.entries(node.data.handles.outputs).forEach(
                  ([key, value]) => {
                    if (edge.targetHandle.endsWith(value)) {
                      node.data.handles.inputs[key] = edge.target;
                      edge.targetHandle = node.id + "_" + value;
                      edge.target = node.id;
                      found = true;
                    }
                  }
                );
                if (found) {
                  break;
                }
              }
            }
          }
          if (edge.source == nodeId) {
            let found = false;
            for (const node of newNodes.reverse()) {
              if (node.id.startsWith(nodeId)) {
                Object.entries(node.data.handles.inputs).forEach(
                  ([key, value]) => {
                    if (edge.sourceHandle?.endsWith(value)) {
                      node.data.handles.outputs[key] = edge.source;
                      edge.sourceHandle = node.id + "_" + value;
                      edge.source = node.id;
                      found = true;
                    }
                  }
                );
                if (found) {
                  break;
                }
              }
            }
          }
        });
        oldNodes = oldNodes.filter((node) => !nodesToRemove.includes(node.id));
        set({
          nodes: [...newNodes, ...oldNodes],
          edges: [...edges, ...newEdges],
        });
      },
      replaceMap: (nodeId: string, newNodes: AppNode[]) => {
        let edges = JSON.parse(JSON.stringify(get().edges));
        let oldNodes = get().nodes;
        const nodesToRemove = [nodeId];
        const edgesToRemove: string[] = [];
        const newEdges = [];
        edges.forEach((edge) => {
          if (edge.target == nodeId) {
            newNodes.forEach((node) => {
              node.data.handles.inputs[
                edge.targetHandle.replace(`${nodeId}_`, "")
              ] = edge.label;
              let newEdge = {
                ...edge,
                target: node.id,
                targetHandle:
                  node.id + "_" + edge.targetHandle.replace(`${nodeId}_`, ""),
                id: edge.id.replace(`${nodeId}`, `${node.id}`),
              };
              newEdges.push(newEdge);
            });
          }
          if (edge.source == nodeId) {
            newNodes.forEach((node) => {
              node.data.handles.outputs[
                edge.sourceHandle.replace(`${nodeId}_`, "")
              ] = edge.label;
              let newEdge = {
                ...edge,
                source: node.id,
                sourceHandle:
                  node.id + "_" + edge.sourceHandle.replace(`${nodeId}_`, ""),
                id: edge.id.replace(`${nodeId}`, `${node.id}`),
              };
              newEdges.push(newEdge);
            });
          }
        });
        oldNodes = oldNodes.filter((node) => !nodesToRemove.includes(node.id));
        edges = edges.filter((edge) => !edgesToRemove.includes(edge.id));
        set({
          nodes: [...newNodes, ...oldNodes],
          edges: [...edges, ...newEdges],
        });
      },
      recalculateNodePositions: () => {
        const data = calculateNodePositions(get().nodes, get().edges);
        const newNodes = get().nodes.map((node) => ({
          ...node,
          position: data.find((position) => position.id === node.id),
        }));
        set({ nodes: newNodes });
      },
    }),
    {
      partialize: (state) => ({
        nodes: state.nodes,
        edges: state.edges,
      }),
      equality: (pastState: AppState, currentState: AppState) => {
        if (
          currentState.nodes.length !== pastState.nodes.length ||
          currentState.edges.length !== pastState.edges.length
        ) {
          return false;
        }
        const pastNodeIds = new Set(pastState.nodes.map((node) => node.id));
        const pastEdgeIds = new Set(pastState.edges.map((edge) => edge.id));
        const allCurrentNodeIdsExistInPast = currentState.nodes.every((node) =>
          pastNodeIds.has(node.id)
        );
        const allCurrentEdgeIdsExistInPast = currentState.edges.every((edge) =>
          pastEdgeIds.has(edge.id)
        );

        if (allCurrentNodeIdsExistInPast && allCurrentEdgeIdsExistInPast) {
          return true;
        }
        return false;
      },
    }
  )
);

export default useStore;
