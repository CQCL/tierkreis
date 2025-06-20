import { addEdge, applyEdgeChanges, applyNodeChanges } from "@xyflow/react";
import { temporal, ZundoOptions } from "zundo";
import { create } from "zustand";

import { initialEdges } from "@/edges/index";
import { calculateNodePositions } from "@/graph/parseGraph";
import { initialNodes } from "@/nodes/index";
import { AppNode, type AppState } from "@/nodes/types";
import { Edge, getOutgoers } from "@xyflow/react";

type PartialState = Pick<AppState, "nodes" | "edges">;
// For type annotation I pulled this out
const options: ZundoOptions<AppState, PartialState> = {
  partialize: (state: AppState): PartialState => ({
    nodes: state.nodes,
    edges: state.edges,
  }),
  equality: (pastState: PartialState, currentState: PartialState) => {
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
};
// this is our useStore hook that we can use in our components to get parts of the store and call actions
const useStore = create<AppState>()(
  temporal(
    (set, get) => ({
      nodes: initialNodes,
      edges: initialEdges,
      info: { type: "Logs", content: "" },
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
      getInfo: () => {
        return get().info;
      },

      replaceEval: (nodeId: string, newNodes: AppNode[], newEdges: Edge[]) => {
        // replaces an eval node with its nested subgraph
        const edges: Edge[] = JSON.parse(JSON.stringify(get().edges)); // is there a better way to do this?
        let oldNodes = get().nodes;
        const nodesToRemove = [nodeId];
        newNodes.sort(
          (
            a,
            b // we only care about the last part of the id as number
          ) =>
            Number(a.id.substring(a.id.lastIndexOf(":"), a.id.length)) -
            Number(b.id.substring(b.id.lastIndexOf(":"), b.id.length))
        );
        edges.forEach((edge) => {
          if (edge.target == nodeId) {
            if (
              edge.label === "Graph Body" &&
              getOutgoers({ id: edge.source }, oldNodes, edges).length === 1
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
                  if (edge.sourceHandle?.endsWith(value)) {
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
        oldNodes = oldNodes.filter((node) => !nodesToRemove.includes(node.id));
        set({
          nodes: [...newNodes, ...oldNodes],
          edges: [...edges, ...newEdges],
        });
      },
      replaceMap: (nodeId: string, newNodes: AppNode[]) => {
        // copy over all the inputs and outputs from the map node to its children
        let edges: Edge[] = JSON.parse(JSON.stringify(get().edges));
        let oldNodes = get().nodes;
        const nodesToRemove = [nodeId];
        const edgesToRemove: string[] = [];
        const newEdges: Edge[] = [];
        edges.forEach((edge) => {
          if (edge.target == nodeId) {
            newNodes.forEach((node) => {
              if (typeof edge.targetHandle === "string") {
                node.data.handles.inputs.push(
                  edge.targetHandle.replace(`${nodeId}_`, "")
                );
              }
              const newEdge = {
                ...edge,
                target: node.id,
                targetHandle:
                  node.id + "_" + edge.targetHandle?.replace(`${nodeId}_`, ""),
                id: edge.id.replace(`${nodeId}`, `${node.id}`),
              };
              newEdges.push(newEdge);
            });
          }
          if (edge.source == nodeId) {
            newNodes.forEach((node) => {
              if (typeof edge.sourceHandle === "string") {
                node.data.handles.outputs.push(
                  edge.sourceHandle.replace(`${nodeId}_`, "")
                );
              }
              const newEdge = {
                ...edge,
                source: node.id,
                sourceHandle:
                  node.id + "_" + edge.sourceHandle?.replace(`${nodeId}_`, ""),
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
          position: data.find((position) => position.id === node.id) || {
            id: "-",
            x: 0,
            y: 0,
          },
        }));
        set({ nodes: newNodes });
      },
    }),
    options
  )
);

export default useStore;
