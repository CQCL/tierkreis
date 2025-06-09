import { useState } from 'react'
import { Handle, Position, type NodeProps } from '@xyflow/react';
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

import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { NodeStatusIndicator } from '@/components/StatusIndicator';
import { type BackendNode } from './types';
import { getLogs } from '@/data/logs';

export function ConstNode({
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
        <CardTitle>Const</CardTitle>
        <CardDescription>Name: {data.name} </CardDescription>
      </CardHeader>

      <CardContent>
            {!Object.keys(data.ports.inputs).length ? null : (
          <>
           <Separator />
            <p>Inputs</p>
              { Object.entries(data.ports.inputs).map(([key, value]) => (
                  <p key={key}>{`${key}: ${value}`}</p>
              ))}
          </>
        )}
        {!Object.keys(data.ports.outputs).length ? null : (
          <>
            <Separator />
            <p>Outputs</p>
              { Object.entries(data.ports.outputs).map(([key, value]) => (
                  <p key= {key}>{`${key}: ${value}`}</p>
              ))}
          </>
        )}
      </CardContent>
      <CardFooter>
        <Sheet>
          <SheetTrigger asChild>
            <Button onClick={() => updateLogs(data.workflowId, data.node_location)}>Logs</Button>
          </SheetTrigger>
          <SheetContent className="max-h-screen overflow-y-scroll"> 
                <SheetHeader>
                  <SheetTitle>Logs</SheetTitle>
                  <SheetDescription className='overflow-auto'>{logs}</SheetDescription>
                </SheetHeader>
          </SheetContent>
        </Sheet>
      </CardFooter>

      <Handle type="source" position={Position.Bottom} />
    </Card>
    </NodeStatusIndicator>
  );
}
