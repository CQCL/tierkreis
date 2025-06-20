import { NodeInfo } from "@/components/info";
import { Dialog } from "@/components/ui/dialog";
import { SidebarProvider } from "@/components/ui/sidebar";
import { WorkflowSidebar } from "@/components/workflow-sidebar";
export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <SidebarProvider>
      <Dialog>
        <WorkflowSidebar />
        <NodeInfo />
        <main>{children}</main>
      </Dialog>
    </SidebarProvider>
  );
}
