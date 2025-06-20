export interface InfoProps {
  type: "Logs" | "Errors";
  content: string;
}

export interface HandleProps {
  handles: string[];
  id: string;
}
