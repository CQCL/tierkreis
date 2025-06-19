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
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { getErrors } from "@/data/logs";
import { type NodeProps } from "@xyflow/react";
import { useState } from "react";
import { type BackendNode } from "./types";
import { URL } from "@/data/constants";

export function DefaultNode({ data }: NodeProps<BackendNode>) {
  const [errors, setErrors] = useState("");
  const updateErrors = (workflowId: string, node_location: string) => {
    getErrors(workflowId, node_location).then((errors) => setErrors(errors));
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
            <Button><a href={`${URL}/${data.workflowId}/nodes/${data.node_location}/logs`} target="_blank">Logs</a></Button>
          {data.status == "Error" && (
            <Sheet>
              <SheetTrigger asChild>
                <Button
                  onClick={() =>
                    updateErrors(data.workflowId, data.node_location)
                  }
                >
                  Errors
                </Button>
              </SheetTrigger>
              <SheetContent className="max-h-screen overflow-y-scroll">
                <SheetHeader>
                  <SheetTitle>Errors</SheetTitle>
                  <SheetDescription>
                    <pre>{errors}</pre>
                  </SheetDescription>
                </SheetHeader>
              </SheetContent>
            </Sheet>
          )}
        </CardFooter>
      </Card>
    </NodeStatusIndicator>
  );
}
