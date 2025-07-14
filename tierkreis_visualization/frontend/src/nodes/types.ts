import { InfoProps } from "@/components/types";
import { type Node } from "@xyflow/react";

export type PyNode = {
  id: string | number;
  status: "Not started" | "Started" | "Error" | "Finished";
  function_name: string;
  node_location: string;
};
export type BackendNode = Node<{
  name: string;
  status: "Not started" | "Started" | "Error" | "Finished";
  handles: {
    inputs: string[];
    outputs: string[];
  };
  workflowId: string;
  node_location: string;
  id: string;
  title: string;
  setInfo: (arg: InfoProps) => void;
  label?: string;
}>;
export type AppNode = BackendNode;
