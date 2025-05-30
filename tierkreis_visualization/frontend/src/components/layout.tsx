import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar"
import { WorkflowSidebar } from "@/components/workflow-sidebar"
 
export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <SidebarProvider>
      <WorkflowSidebar />
      <main>
        <SidebarTrigger />
        {children}
      </main>
    </SidebarProvider>
  )
}
