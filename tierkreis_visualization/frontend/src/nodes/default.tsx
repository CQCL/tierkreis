import { useState } from 'react'
import { type NodeProps } from '@xyflow/react';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet"
import { NodeStatusIndicator } from '@/components/StatusIndicator';
import { Button } from '@/components/ui/button';
import { type BackendNode } from './types';
import { InputHandleArray, OutputHandleArray } from '@/components/handles';
import { getLogs } from '@/data/logs';

export function DefaultNode({
  data,
}: NodeProps<BackendNode>) {
  const [logs, setLogs] = useState("")
  const updateLogs = (workflowId: string, node_location: string) => {
    getLogs(workflowId, node_location)
      .then(logs => setLogs(logs))
  }
  return (
    <NodeStatusIndicator status={data.status}>
      <Card className="w-[350px]">
        <CardHeader>
          <CardTitle>{data.title}</CardTitle>
          <CardDescription>Name: {data.node_location} </CardDescription>
        </CardHeader>
        <CardContent>
          <InputHandleArray handles={data.handles.inputs} id={data.id} />
          <OutputHandleArray handles={data.handles.outputs} id={data.id} />
        </CardContent>
        <CardFooter>
          <Sheet>
            <SheetTrigger asChild>
              <Button onClick={() => updateLogs(data.workflowId, data.node_location)}>Logs</Button>
            </SheetTrigger>
            <SheetContent className="max-h-screen overflow-y-scroll">
              <SheetHeader>
                <SheetTitle>Logs</SheetTitle>
                <SheetDescription>{logs}</SheetDescription>
              </SheetHeader>
            </SheetContent>
          </Sheet>
        </CardFooter>

      </Card>
    </NodeStatusIndicator>
  );
}
