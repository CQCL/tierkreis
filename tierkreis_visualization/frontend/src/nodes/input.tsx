import { Handle, Position, type NodeProps } from '@xyflow/react';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { NodeStatusIndicator } from '@/components/StatusIndicator';

import { type BackendNode } from './types';

export function InputNode({
  data,
}: NodeProps<BackendNode>) {

  return (
    <NodeStatusIndicator status={data.status}>
    <Card className="w-[350px]">
      <CardHeader>
        <CardTitle>Input</CardTitle>
        <CardDescription>Name: {data.name} </CardDescription>
      </CardHeader>

      <CardContent>
            {!Object.keys(data.ports.inputs).length ? null : (
          <>
            <p>Inputs</p>
              { Object.entries(data.ports.inputs).map(([key, value]) => (
                  <p key={key}>{`${key}: ${value}`}</p>
              ))}
          </>
        )}
        {!Object.keys(data.ports.outputs).length ? null : (
          <>
            <p>Outputs</p>
              { Object.entries(data.ports.outputs).map(([key, value]) => (
                  <p key= {key}>{`${key}: ${value}`}</p>
              ))}
          </>
        )}
      </CardContent>
      <CardFooter>
        <p>Logs</p>
      </CardFooter>
      <Handle type="target" position={Position.Top} />
      <Handle type="source" position={Position.Bottom} />
    </Card>
    </NodeStatusIndicator>
  );
}
