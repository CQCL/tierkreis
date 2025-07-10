import { NodeInfo } from "@/components/info";
import { Dialog } from "@/components/ui/dialog";
import { SidebarProvider } from "@/components/ui/sidebar";
import { WorkflowSidebar } from "@/components/workflow-sidebar";
import { Workflow } from "@/components/types";

export default function Layout({
  children,
  workflows,
  workflowId,
}: {
  children: React.ReactNode;
  workflows: Workflow[];
  workflowId: string;
}) {
  return (
    <SidebarProvider>
      <Dialog>
        <WorkflowSidebar workflows={workflows} workflowId={workflowId} />
        <NodeInfo />
        <main>{children}</main>
      </Dialog>
    </SidebarProvider>
  );
}
