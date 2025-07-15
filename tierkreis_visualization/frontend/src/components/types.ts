export interface InfoProps {
  type: "Logs" | "Errors";
  content: string;
}
export interface Workflow {
  id: string;
  name: string;
}

export interface HandleProps {
  handles: string[];
  id: string;
}
