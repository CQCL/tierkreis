import { InputHandleArray, OutputHandleArray } from "@/components/handles";
import { NodeStatusIndicator } from "@/components/StatusIndicator";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { DialogTrigger } from "@/components/ui/dialog";
import { getErrors, getLogs } from "@/data/logs";
import { type NodeProps } from "@xyflow/react";
import { useShallow } from "zustand/react/shallow";
import { AppState, type BackendNode } from "./types";

import useStore from "@/data/store";

const selector = (state: AppState) => ({
  setInfo: state.setInfo,
});

export function DefaultNode({ data }: NodeProps<BackendNode>) {
  const { setInfo } = useStore(useShallow(selector));
  const updateErrors = (workflowId: string, node_location: string) => {
    getErrors(workflowId, node_location).then((errors) =>
      setInfo({ type: "Errors", content: errors })
    );
  };
  const updateLogs = (workflowId: string, node_location: string) => {
    getLogs(workflowId, node_location).then((logs) => {
      console.log(logs);
      setInfo({ type: "Logs", content: logs });
    });
  };
  return (
    <NodeStatusIndicator status={data.status}>
      <Card className="w-[350px]">
        <CardHeader>
          <CardTitle>{data.title}</CardTitle>
          <CardDescription>
            Name: {data.title == "Function" ? data.name : data.node_location}{" "}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <InputHandleArray handles={data.handles.inputs} id={data.id} />
          <OutputHandleArray handles={data.handles.outputs} id={data.id} />
        </CardContent>
        <CardFooter className="flex justify-between">
          <DialogTrigger asChild>
            <Button
              onClick={() => updateLogs(data.workflowId, data.node_location)}
            >
              Logs
            </Button>
          </DialogTrigger>
          {data.status == "Error" && (
            <DialogTrigger asChild>
              <Button
                onClick={() =>
                  updateErrors(data.workflowId, data.node_location)
                }
              >
                Errors
              </Button>
            </DialogTrigger>
          )}
        </CardFooter>
      </Card>
    </NodeStatusIndicator>
  );
}
