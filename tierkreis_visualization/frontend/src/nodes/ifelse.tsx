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

import { type BackendNode } from './types';

export function IfElseNode({
  data,
}: NodeProps<BackendNode>) {

  return (
    <Card className="w-[350px]">
      <CardHeader>
        <CardTitle>IfElse</CardTitle>
        <CardDescription>Name: {data.name} </CardDescription>
      </CardHeader>

      <CardContent>
            <span>{`Value ${data.outputs[0].value}`}</span>
      </CardContent>
      <CardFooter>
        <Button>Logs</Button>
      </CardFooter>

      <Handle type="source" position={Position.Bottom} />
      <Handle type="target" position={Position.Top} />
    </Card>
  );
}
