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
        {
          data.outputs.map((output, index) => (
            <div key={index}>
              <span>{`Output ${index + 1}: ${output.name}`}</span>
              <p>{`Value: ${output.value}`}</p>
            </div>
          ))
        }
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
