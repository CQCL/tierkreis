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
import { parseNodes } from "@/nodes/parseNodes";
import { parseEdges } from "@/edges/parseEdges";

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
  const setUrl = useStore((state) => state.setUrl);
  const getUrl = useStore((state) => state.getUrl);
  const updateNodes = async (url: string) => {
    setUrl(url);
    let json = fetch(url, { method: 'GET', headers: { 'Accept': 'application/json' } })
      .then(response => response.json());
    json.then(data => parseNodes(data)).then(nodes => setNodes(nodes));
    json.then(data => parseEdges(data)).then(edges => setEdges(edges));

  }
  useEffect(() => {
    const url = getUrl();
    if (url === "") {
      return;
    }
    const ws = new WebSocket(url);
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setNodes(parseNodes(data.nodes));
      setEdges(parseEdges(data.edges));
    };
    return () => {
      ws.close();
    };
  }, [setUrl]);

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
                    <a onClick={() => updateNodes(item.url)}>
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
