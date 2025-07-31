export interface InfoProps {
  type: "Logs" | "Errors";
  content: string;
}
export interface Workflow {
  id: string;
  name: string;
  start: string;
}

export interface HandleProps {
  handles: string[];
  id: string;
}
