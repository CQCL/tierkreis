export interface InfoProps {
  type: "Logs" | "Errors";
  content: string;
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
  onOpenChange: (open: boolean) => void;
}
