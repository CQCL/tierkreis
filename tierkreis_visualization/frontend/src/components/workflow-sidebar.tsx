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
} from "@/components/ui/sidebar"


import useStore from "@/data/store";
import { URL } from "@/data/constants"
import { parseGraph, parseNodes, parseEdges } from "@/graph/parseGraph";


export function WorkflowSidebar() {
  const [items, setItems] = useState([])
  useEffect(() => {
    function getWorkflows(url: string) {
      fetch(`${url}/all`, { method: "GET", headers: { "Content-Type": "application/json" } })
        .then(response => response.json())
        .then(data => data.map((workflow) => {
          return {
            id: workflow.id,
            name: workflow.name,
            url: `${url}/${workflow.id}/nodes/-`,
          };
        }))
        .then(items => setItems(items));
    }
    getWorkflows(URL)
  }, []);
  const setEdges = useStore((state) => state.setEdges);
  const setNodes = useStore((state) => state.setNodes);
  const setWorkflowId = useStore((state) => state.setWorkflowId);
  const getWorkflowId = useStore((state) => state.getWorkflowId);
  const updateNodes = async (workflowId: string) => {
    setWorkflowId(workflowId);
    const url = `${URL}/${workflowId}/nodes/-`;
    fetch(url, { method: 'GET', headers: { 'Accept': 'application/json' } })
      .then(response => response.json())
      .then(data => parseGraph(data, workflowId)).then(graph => {
        setNodes(graph.nodes);
        setEdges(graph.edges);
      })
  }
  useEffect(() => {
    const workflowId = getWorkflowId();
    if (workflowId === "") {
      return;
    }
    const url = `${URL}/${workflowId}/nodes/-`;
    const ws = new WebSocket(url);
    ws.onmessage = (event) => {
      //TODO: update status only
      const data = JSON.parse(event.data);
      setNodes(parseNodes(data.nodes, workflowId));
      setEdges(parseEdges(data.edges));
    };
    return () => {
      ws.close();
    };
  }, [setWorkflowId]);

  return (
    <Sidebar>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Workflows</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {items.map((item) => (
                <SidebarMenuItem key={item.id}>
                  <SidebarMenuButton asChild>
                    <a onClick={() => updateNodes(item.id)}>
                      <span>{item.name}</span>
                    </a>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
    </Sidebar>
  )
}
