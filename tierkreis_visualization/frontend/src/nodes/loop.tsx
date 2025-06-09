import { Handle, Position, type NodeProps } from '@xyflow/react';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { NodeStatusIndicator } from '@/components/StatusIndicator';
import { type BackendNode } from './types';

export function LoopNode({
  data,
}: NodeProps<BackendNode>) {

  return (
    <NodeStatusIndicator status={data.status}>
    <Card className="w-[350px]">
      <CardHeader>
        <CardTitle>Loop</CardTitle>
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
        <Button>Logs</Button>
      </CardFooter>

      <Handle type="source" position={Position.Bottom} />
      <Handle type="target" position={Position.Top} />
    </Card>
    </NodeStatusIndicator>
  );
}
