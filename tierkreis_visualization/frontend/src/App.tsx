import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "react-router";
import { useEffect } from "react";
import { useReactFlow } from "@xyflow/react";

import Layout from "@/components/layout";
import Flow from "@/components/flow";
import { URL } from "@/data/constants";
import { Workflow } from "@/components/types";
import { parseGraph } from "@/graph/parseGraph";
import { PartialState } from "@/data/store";
import { bottomUpLayout } from "./graph/layoutGraph";

function fromStorage(workflowId: string): PartialState {
  const storedData = localStorage.getItem(workflowId);
  try {
    return JSON.parse(storedData || "{}") as PartialState;
  } catch (error) {
    return { workflowId: "", nodes: [], edges: [] } as PartialState;
  }
}

function useGraph(workflowId: string) {
  // get graphData from backend
  return useQuery({
    queryKey: ["workflowGraph", workflowId],
    queryFn: async () => {
      const response = await fetch(`${URL}/${workflowId}/nodes/-`, {
        method: "GET",
        headers: { Accept: "application/json" },
      });
      if (!response.ok) {
        throw new Error("Network response was not ok");
      }
      return response.json();
    },
    enabled: !!workflowId,
    select: (data) => parseGraph(data, workflowId),
  });
}

function useWorkflows(url: string) {
  // get workflow ids from backend
  return useQuery<Workflow[]>({
    queryKey: ["workflows", url],
    queryFn: async () => {
      const response = await fetch(`${url}/all`);
      if (!response.ok) {
        throw new Error("Network response was not ok");
      }
      return response.json();
    },
    select: (data) =>
      data.map(
        (workflow): Workflow => ({
          id: workflow.id,
          name: workflow.name,
        })
      ),
    staleTime: 1000 * 60 * 5, // Cache for 5 minutes
  });
}

export default function App() {
  const { data: items = [] } = useWorkflows(URL);
  const { workflowId = "" } = useParams();
  const { data: graph, ...graphQuery } = useGraph(workflowId);
  const queryClient = useQueryClient();

  const { nodes: storedNodes, edges: storedEdges } = fromStorage(workflowId);
  let nodes = [], edges = [];
  const reactFlowInstance = useReactFlow();
  if (graphQuery.isPending || graphQuery.isError || !graph) {
    console.log("Using stored state or empty graph");
    // use the stored state, if not available, should be empty
    if (storedNodes && storedEdges) {
      nodes = storedNodes;
      edges = storedEdges;
    }
  } else if (!storedNodes && !storedEdges) {
    console.log("No stored state found, using backend graph");
    // if no stored state, use the graph from the backend
    nodes = bottomUpLayout(graph.nodes, graph.edges);
    edges = graph.edges;
    // here we don't have position info -> calculate
  } else {
    // merge the stored state with the graph from the backend
    const mergedNodes = graph.nodes.map((node) => ({
      ...node,
      position: storedNodes.find((oldNode) => oldNode.id === node.id)
        ?.position || {
        id: "-",
        x: 0,
        y: 0,
      },
    }));
    const edgesMap = new Map();
    storedEdges.forEach((edge) => edgesMap.set(edge.id, edge));
    graph.edges.forEach((edge) => edgesMap.set(edge.id, edge));
    const mergedEdges = [...edgesMap.values()];
    console.log("Merging", mergedNodes, mergedEdges);
    nodes = storedNodes;
    edges = mergedEdges;
  }

  useEffect(() => {
    if (workflowId) {
      const ws = new WebSocket(`${URL}/${workflowId}/nodes/-`);
      ws.onmessage = (event) => {
        const graph = parseGraph(JSON.parse(event.data), workflowId);
        queryClient.setQueryData(["workflowGraph", workflowId], graph);
        // do merging too
        reactFlowInstance.setNodes(graph.nodes);
        reactFlowInstance.setEdges(graph.edges);
      };
      return () => {
        if (ws.readyState == WebSocket.OPEN) {
          ws.close();
        }
      };
    }
  }, [workflowId, queryClient, reactFlowInstance]);
  reactFlowInstance.setNodes(nodes);
  reactFlowInstance.setEdges(edges);
  return (
    <Layout workflows={items} workflowId={workflowId}>
      <Flow workflowId={workflowId} />
    </Layout>
  );
}
