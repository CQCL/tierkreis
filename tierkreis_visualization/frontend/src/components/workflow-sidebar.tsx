import { useEffect, useState } from "react";

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

export function WorkflowSidebar() {
  const [items, setItems] = useState<{ id: string; name: string }[]>([]);
  const { workflowId = "" } = useParams();
  useEffect(() => {
    function getWorkflows(url: string) {
      fetch(`${url}/all`, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      })
        .then((response) => response.json())
        .then((data) =>
          data.map((workflow: { id: string; name: string }) => {
            return {
              id: workflow.id,
              name: workflow.name,
            };
          })
        )
        .then((items) => {
          setItems(items);
        });
    }
    getWorkflows(URL);
  }, []);
  const { setEdges, setNodes } = useStore();
  const { clear } = useStore.temporal.getState();

  useEffect(() => {
    if (workflowId === "") {
      return;
    }
    const url = `${URL}/${workflowId}/nodes/-`;
    fetch(url, { method: "GET", headers: { Accept: "application/json" } })
      .then((response) => response.json())
      .then((data) => parseGraph(data, workflowId))
      .then((graph) => {
        setNodes(graph.nodes);
        setEdges(graph.edges);
      });
    const ws = new WebSocket(url);
    ws.onmessage = (event) => {
      //TODO: update status only
      const graph = parseGraph(JSON.parse(event.data), workflowId);
      setEdges(graph.edges);
      setNodes(graph.nodes);
    };
    return () => {
      if (ws.readyState == WebSocket.OPEN) {
        ws.close();
      }
    };
  }, [setEdges, setNodes, workflowId]);

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
                    onClick={() => clear()}
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
