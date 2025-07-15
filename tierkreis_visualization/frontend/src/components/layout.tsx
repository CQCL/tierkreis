import { NodeInfo } from "@/components/info";
import { Dialog } from "@/components/ui/dialog";
import { SidebarProvider } from "@/components/ui/sidebar";
import { WorkflowSidebar } from "@/components/workflow-sidebar";
import { InfoProps, Workflow } from "@/components/types";

export default function Layout({
  children,
  workflows,
  workflowId,
  info,
}: {
  children: React.ReactNode;
  workflows: Workflow[];
  workflowId: string;
  info: InfoProps;
}) {
  return (
    <SidebarProvider>
      <Dialog>
        <WorkflowSidebar workflows={workflows} workflowId={workflowId} />
        <NodeInfo info={info} />
        <main>{children}</main>
      </Dialog>
    </SidebarProvider>
  );
}
