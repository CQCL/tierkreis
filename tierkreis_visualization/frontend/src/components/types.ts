export interface InfoProps {
  type: "Logs" | "Errors";
  content: string;
  workflowId: string;
  node_location: string;
}
export interface Workflow {
  id: string;
  name: string;
  start_time: string;
}

export interface HandleProps {
  handles: string[];
  id: string;
  isOpen: boolean;
  hoveredId: string;
  setHoveredId: (id: string) => void;
}
