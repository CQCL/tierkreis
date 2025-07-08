import { useEffect, useState } from "react";
import { InputHandleArray, OutputHandleArray } from "@/components/handles";
import { NodeStatusIndicator } from "@/components/StatusIndicator";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { DialogTrigger } from "@/components/ui/dialog";
import { useErrors, useLogs } from "@/data/logs";
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
  const [infoState, setInfoState] = useState<{
    workflowId: string;
    node_location: string;
    error: boolean;
  }>({
    workflowId: "",
    node_location: "",
    error: false,
  });
  const { data: logs } = useLogs(infoState.workflowId, infoState.node_location);
  const { data: errors } = useErrors(
    infoState.workflowId,
    infoState.node_location
  );
  useEffect(() => {
    if (infoState.error) {
      setInfo({ type: "Errors", content: errors ? errors : "" });
    } else {
      setInfo({ type: "Logs", content: logs ? logs : "" });
    }
  }, [infoState, logs, errors, setInfo]);

  return (
    <NodeStatusIndicator status={data.status}>
      <Card className="w-[180px]">
        <DialogTrigger asChild>
          <div
            onClick={(event) => {
              //workaround to render errors
              const target = event.target as HTMLElement;
              if (target.closest("button") === null) {
                setInfoState({
                  workflowId: data.workflowId,
                  node_location: data.node_location,
                  error: false,
                });
              }
            }}
          >
            <CardHeader>
              <CardTitle
                style={{ whiteSpace: "normal", wordBreak: "break-word" }}
              >
                {data.title == "Function" ? data.name : data.title}
              </CardTitle>
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
                    setInfoState({
                      workflowId: data.workflowId,
                      node_location: data.node_location,
                      error: true,
                    })
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
