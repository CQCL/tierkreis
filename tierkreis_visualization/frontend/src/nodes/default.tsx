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
import { type BackendNode } from "./types";
import { OctagonAlert } from "lucide-react";

export function DefaultNode({ data }: NodeProps<BackendNode>) {
  const { data: logs } = useLogs(
    data.workflowId,
    data.node_location,
    data.title
  );
  const { data: errors } = useErrors(
    data.workflowId,
    data.node_location,
    data.status
  );
  return (
    <NodeStatusIndicator status={data.status}>
      <Card className="w-[180px]">
        <DialogTrigger asChild>
          <div
            onClick={(event) => {
              //workaround to render errors
              const target = event.target as HTMLElement;
              if (target.closest("button") === null) {
                if (data.title == "Function") {
                  data.setInfo({ type: "Logs", content: logs ? logs : "" });
                }
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
                    data.setInfo({
                      type: "Errors",
                      content: errors ? errors : "",
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
