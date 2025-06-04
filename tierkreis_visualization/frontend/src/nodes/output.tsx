import { Handle, Position, type NodeProps } from '@xyflow/react';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"

import { type BackendNode } from './types';

export function OutputNode({
  data,
}: NodeProps<BackendNode>) {

  return (
    <Card className="w-[350px]">
      <CardHeader>
        <CardTitle>Output</CardTitle>
        <CardDescription>Name: {data.name} </CardDescription>
      </CardHeader>
      <CardContent>
            <span>{`Value ${data.outputs[0].value}`}</span>
      </CardContent>
      <CardFooter>
        <p>Logs</p>
      </CardFooter>

      <Handle type="target" position={Position.Top} />
      <Handle type="source" position={Position.Bottom} />
    </Card>
  );
}
