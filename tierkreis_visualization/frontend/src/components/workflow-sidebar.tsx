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
import { useQuery } from "@tanstack/react-query";
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

  useEffect(() => {
    if (!workflowId) {
      return;
    }
    const url = `${URL}/${workflowId}/nodes/-`;
    setNodes([], true);
    setEdges([]);
    if (!tryFromStorage(workflowId)) {
      fetch(url, { method: "GET", headers: { Accept: "application/json" } })
        .then((response) => response.json())
        .then((data) => parseGraph(data, workflowId))
        .then((graph) => {
          setNodes(graph.nodes, false);
          setEdges(graph.edges);
          recalculateNodePositions();
          setWorkflowId(workflowId);
        });
    }
    const ws = new WebSocket(url);
    ws.onmessage = (event) => {
      const graph = parseGraph(JSON.parse(event.data), workflowId);
      setEdges(graph.edges);
      setNodes(graph.nodes, true);
    };
    return () => {
      if (ws.readyState == WebSocket.OPEN) {
        ws.close();
      }
    };
  }, [
    tryFromStorage,
    recalculateNodePositions,
    setEdges,
    setNodes,
    setWorkflowId,
    workflowId,
  ]);

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
