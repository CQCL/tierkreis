import { SidebarProvider } from "@/components/ui/sidebar"
import { WorkflowSidebar } from "@/components/workflow-sidebar"
 
export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <SidebarProvider>
      <WorkflowSidebar />
      <main>
        {children}
      </main>
    </SidebarProvider>
  )
}
