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

import useStore from "@/data/store";
import { URL } from "@/data/constants";
import { parseGraph } from "@/graph/parseGraph";

export function WorkflowSidebar() {
  const [items, setItems] = useState([]);
  const { workflowId = "" } = useParams();
  useEffect(() => {
    function getWorkflows(url: string) {
      fetch(`${url}/all`, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      })
        .then((response) => response.json())
        .then((data) =>
          data.map((workflow) => {
            return {
              id: workflow.id,
              name: workflow.name,
              url: `${url}/${workflow.id}/nodes/-`,
            };
          })
        )
        .then((items) => {setItems(items)});
    }
    getWorkflows(URL);
  }, []);
  const { setEdges, setNodes } = useStore();
  const { clear } = useStore.temporal.getState();

  useEffect(() => {
    const url = `${URL}/${workflowId}/nodes/-`;
    fetch(url, { method: "GET", headers: { Accept: "application/json" } })
      .then((response) => response.json())
      .then((data) => parseGraph(data, workflowId))
      .then((graph) => {
        setNodes(graph.nodes);
        setEdges(graph.edges);
      });
    if (workflowId === "") {
      return;
    }
    
    //TODO: use websocket to update nodes and edges
    const ws = new WebSocket(url);
    ws.onmessage = (event) => {
      //TODO: update status only
      parseGraph(JSON.parse(event.data), workflowId).then((graph) => {
      setEdges(graph.edges);
      setNodes(graph.nodes);
      });
    };
    return () => {
      ws.close();
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
                  <SidebarMenuButton asChild isActive={workflowId === item.id} onClick={() => clear()}>
                      <Link to={`/${item.id}`}><span>{item.name}</span></Link>
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
