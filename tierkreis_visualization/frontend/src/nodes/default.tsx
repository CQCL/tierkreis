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
import { OctagonAlert } from "lucide-react";
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
      setInfo({ type: "Logs", content: logs });
    });
  };
  return (
    <NodeStatusIndicator status={data.status}>
      <Card className="w-[180px]">
        <DialogTrigger asChild>
          <div
            onClick={(event) => {
              //workaround to render errors
              const target = event.target as HTMLElement;
              if (target.closest("button") === null) {
                updateLogs(data.workflowId, data.node_location);
              }
            }}
          >
            <CardHeader>
              <CardTitle style={{ whiteSpace: "normal", wordBreak: "break-word" }}>{data.title == "Function"? data.name :data.title}</CardTitle>
            </CardHeader>
            <CardContent>
              <InputHandleArray handles={data.handles.inputs} id={data.id} />
              <OutputHandleArray handles={data.handles.outputs} id={data.id} />
            </CardContent>
            <CardFooter className="flex items-center justify-center">
              {data.status == "Error" && (
                <Button
                  size="sm"
                  variant="destructive"
                  style={{ zIndex: 5 }}
                  onClick={() =>
                    updateErrors(data.workflowId, data.node_location)
                  }
                >
                  <OctagonAlert />
                </Button>
              )}
            </CardFooter>
          </div>
        </DialogTrigger>
      </Card>
    </NodeStatusIndicator>
  );
}
