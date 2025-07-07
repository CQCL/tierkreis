import { addEdge, applyEdgeChanges, applyNodeChanges } from "@xyflow/react";
import { temporal, ZundoOptions } from "zundo";
import { create } from "zustand";

import equal from "fast-deep-equal";
import throttle from "just-throttle";

import { initialEdges } from "@/edges/index";
import { calculateNodePositions } from "@/graph/parseGraph";
import { initialNodes } from "@/nodes/index";
import { AppNode, type AppState } from "@/nodes/types";
import { Edge, getOutgoers } from "@xyflow/react";
import { nodeHeight, nodeWidth } from "@/data/constants";
import { CSSProperties } from "react";

type PartialState = Pick<AppState, "nodes" | "edges" | "workflowId">;
// For type annotation I pulled this out
const options: ZundoOptions<AppState, PartialState> = {
  partialize: (state: AppState): PartialState => ({
    workflowId: state.workflowId,
    nodes: state.nodes,
    edges: state.edges,
  }),
  equality: equal,
  onSave: (_: PartialState, newState: PartialState) => {
    if (
      typeof window !== "undefined" &&
      newState &&
      newState.workflowId != "" &&
      newState.nodes.length > 0
    ) {
      window.localStorage.setItem(
        newState.workflowId,
        JSON.stringify(newState)
      );
    }
  },
  handleSet: (handleSet) => {
    const debouncedHandleSet = throttle(
      (...args: Parameters<typeof handleSet>) => {
        handleSet(...args);
      },
      500,
      { trailing: true, leading: false }
    );

    return (...args: Parameters<typeof handleSet>) => {
      debouncedHandleSet(...args);
    };
  },
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
      setNodes: (nodes, overwritePositions = false) => {
        const oldNodes = get().nodes;
        if (!overwritePositions) {
          const newNodes = nodes.map((node) => ({
            ...node,
            position: oldNodes.find((oldNode) => oldNode.id === node.id)
              ?.position || {
              id: "-",
              x: 0,
              y: 0,
            },
          }));
          set({ nodes: newNodes });
        } else {
          set({ nodes });
        }
      },
      setEdges: (edges) => {
        set({ edges });
      },
      setInfo: (info) => {
        set({ info });
      },
      setWorkflowId: (workflowId) => {
        set({ workflowId });
      },
      replaceEval: (nodeId, newNodes, newEdges) => {
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
        const groupNode = {
          id: nodeId,
          type: "group",
          position: { x: 0, y: 0 },
          data: {},
          parentId: oldNodes.find((node) => node.id === nodeId)?.parentId,
        };
        oldNodes = oldNodes.filter((node) => !nodesToRemove.includes(node.id));
        const tmpEdges = edges.filter(
          (edge) => edge.target !== nodeId && edge.source !== nodeId
        );
        // This is a memory leak, should only add ones we don't know about yet
        get().oldEdges.push(...get().edges);
        set({
          //@ts-expect-error the group node is not a BackendNode but that's not an issue
          nodes: [groupNode, ...oldNodes, ...newNodes],
          edges: [...tmpEdges, ...newEdges],
        });
      },

      replaceMap: (nodeId, newNodes) => {
        // copy over all the inputs and outputs from the map node to its children
        let edges: Edge[] = JSON.parse(JSON.stringify(get().edges));
        let oldNodes = get().nodes;
        const nodesToRemove = [nodeId];
        const edgesToRemove: string[] = [];
        const newEdges: Edge[] = [];
        edges.forEach((edge) => {
          if (edge.target == nodeId) {
            edgesToRemove.push(edge.id);
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
            edgesToRemove.push(edge.id);
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
        const groupNode = {
          id: nodeId,
          type: "group",
          position: { x: 0, y: 0 },
          data: {},
          parentId: oldNodes.find((node) => node.id === nodeId)?.parentId,
        };
        oldNodes = oldNodes.filter((node) => !nodesToRemove.includes(node.id));

        get().oldEdges.push(...edges);
        edges = edges.filter((edge) => !edgesToRemove.includes(edge.id));
        // there are no edges between the newNodes
        set({
          //@ts-expect-error see replaceEval-> group node
          nodes: [groupNode, ...oldNodes, ...newNodes],
          edges: [...edges, ...newEdges],
        });
      },
      recalculateNodePositions: () => {
        const newNodes = bottomUpLayout(get().nodes, [
          ...get().edges,
          ...get().oldEdges,
        ]);
        set({ nodes: newNodes });
      },
      clearOldEdges: () => {
        set({ oldEdges: [] });
      },
      tryFromStorage: (workflowId) => {
        const stored = fromStorage(workflowId);
        if (stored.workflowId === workflowId && stored.nodes.length > 0) {
          //for some reason this is necessary to correctly render all edges
          setTimeout(() => {
            set(stored);
          }, 0);
          return true;
        }
        return false;
      },
    }),
    options
  )
);

interface ShallowNode {
  id: string;
  style?: CSSProperties;
  position: { x: number; y: number };
  parentId?: string;
}

function bottomUpLayout(nodes: AppNode[], edges: Edge[]) {
  // sort nodes by levels i.e. number of : in their id
  // calculate each level individually
  const nodeLevels = new Map<number, ShallowNode[]>();
  nodes.forEach((node) => {
    const level = node.id.split(":").length - 1;
    if (!nodeLevels.has(level)) {
      nodeLevels.set(level, []);
    }
    nodeLevels.get(level)?.push({
      id: node.id,
      style: node.style,
      position: node.position,
      parentId: node.parentId,
    });
  });
  const newNodes: AppNode[] = [];
  let previousNodes: ShallowNode[] = [];
  // construct graph from most nested level
  const levelKeys = Array.from(nodeLevels.keys()).sort((a, b) => b - a);
  for (const level of levelKeys) {
    const padding = level == 0 ? 1 : 20;
    const currentNodes = nodeLevels.get(level);
    if (!currentNodes) continue;
    const idsInLevel = new Set(currentNodes.map((nodeInfo) => nodeInfo.id));
    const levelNodes = nodes.filter((node) => idsInLevel.has(node.id));
    const levelEdges = edges.filter(
      (edge) => idsInLevel.has(edge.source) && idsInLevel.has(edge.target)
    );
    resizeNodes(levelNodes, previousNodes, 20);
    const data = calculateNodePositions(levelNodes, levelEdges, padding);
    const tmpNodes = levelNodes.map((node) => ({
      ...node,
      position: data.find((position) => position.id === node.id) || {
        id: "-",
        x: 0,
        y: 0,
      },
    }));
    newNodes.push(...tmpNodes);
    previousNodes = tmpNodes;
  }
  return newNodes.reverse();
}

function resizeNodes(
  nodesToResize: ShallowNode[],
  childNodes: ShallowNode[],
  padding: number
) {
  // resizes all the nodes in nodesToResize to fit their children
  if (!childNodes.length) return;
  for (const node of nodesToResize) {
    const children = childNodes.filter((child) => child.parentId === node.id);
    if (!children.length) continue;
    const dim = children.reduce(
      (acc, node) => {
        acc.width = Math.max(
          acc.width,
          node.position.x + (Number(node.style?.width) || nodeWidth)
        );
        acc.height = Math.max(
          acc.height,
          node.position.y + (Number(node.style?.height) || nodeHeight)
        );
        return acc;
      },
      { width: 0, height: 0 }
    );
    node.style = { width: dim.width + padding, height: dim.height + padding };
  }
}

function fromStorage(workflowId: string): PartialState {
  const storedData = localStorage.getItem(workflowId);
  try {
    return JSON.parse(storedData || "{}") as PartialState;
  } catch (error) {
    return { workflowId: "", nodes: [], edges: [] } as PartialState;
  }
}

export default useStore;
