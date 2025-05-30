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


import  useStore  from "@/data/store";
import { url } from "@/data/constants"
import { parseNodes } from "@/nodes/parseNodes";

// Menu items.
const items = await getWorkflows(url)

  
async function getWorkflows(url: string) {
  const response = await fetch(`${url}/all`, { method: "GET", headers: { "Content-Type": "application/json"  }});
  const data = await response.json();
  console.log(data);
  return data.map((workflow) => {
     return {
      id: workflow.id,
      name: workflow.name,
      url: `${url}/${workflow.id}/nodes/-`,
    };

  });
}




const updateNodes = async (url: string) => {
  fetch(url, { method: 'GET', headers: { 'Accept': 'application/json' } })
  .then( response => response.json())
  .then(data => parseNodes(data))
  .then(nodes => useStore.setState({nodes}))
}


export function WorkflowSidebar() {
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
                    <a onClick = {() => updateNodes(item.url)}>
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
