import { useEffect } from "react";

import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { Link, useParams } from "react-router";

import { URL } from "@/data/constants";
import useStore from "@/data/store";
import { parseGraph } from "@/graph/parseGraph";
import { useQuery, useQueryClient } from "@tanstack/react-query";
interface Workflow {
  id: string;
  name: string;
}

function useWorkflows(url: string) {
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

export function WorkflowSidebar() {
  const { data: items = [] } = useWorkflows(URL);
  const { workflowId = "" } = useParams();
  const {
    setWorkflowId,
    setEdges,
    setNodes,
    clearOldEdges,
    recalculateNodePositions,
    tryFromStorage,
  } = useStore();
  const { clear } = useStore.temporal.getState();
  const queryClient = useQueryClient();

  const { data: graph } = useQuery({
    queryKey: ["workflowGraph", workflowId],
    queryFn: async () => {
      console.log("Fetching graph for workflowId:", workflowId);
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
    // initialData
  });
  useEffect(() => {
    setNodes([], false);
    setEdges([]);
    if (!tryFromStorage(workflowId) && graph) {
      setNodes(graph.nodes, false);
      setEdges(graph.edges);
      recalculateNodePositions();
    }
  }, [
    graph,
    workflowId,
    recalculateNodePositions,
    setEdges,
    setNodes,
    tryFromStorage,
  ]);
  useEffect(() => {
    if (workflowId) {
      setWorkflowId(workflowId);
      const ws = new WebSocket(`${URL}/${workflowId}/nodes/-`);
      ws.onmessage = (event) => {
        const graph = parseGraph(JSON.parse(event.data), workflowId);
        queryClient.setQueryData(["workflowGraph", workflowId], graph);
        setNodes(graph.nodes, false);
        setEdges(graph.edges);
      };
      return () => {
        if (ws.readyState == WebSocket.OPEN) {
          ws.close();
        }
      };
    }
  }, [workflowId, queryClient, setWorkflowId, setEdges, setNodes]);

  return (
    <Sidebar>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Workflows </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {items.map((item) => (
                <SidebarMenuItem key={item.id}>
                  <SidebarMenuButton
                    asChild
                    isActive={workflowId === item.id}
                    onClick={() => {
                      clearOldEdges(); // not part of the tracked state
                      clear();
                    }}
                  >
                    <Link to={`/${item.id}`}>
                      <span>{item.name}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
    </Sidebar>
  );
}
