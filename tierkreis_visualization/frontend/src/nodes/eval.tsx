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

import useStore from "@/data/store";
import { parseNodes, parseEdges } from "@/graph/parseGraph";

import { type BackendNode } from './types';


const tmpURL = "http://localhost:8000/workflows/00000000-0000-0000-0000-000000000001/nodes/-.N3"

export function EvalNode({
  data,
}: NodeProps<BackendNode>) {
  const appendEdges = useStore((state) => state.appendEdges);
  const appendNodes = useStore((state) => state.appendNodes);
  const loadChildren = async (url: string, parentId: string) => {
  let json = fetch(url, { method: 'GET', headers: { 'Accept': 'application/json' } })
    .then(response => response.json());
  json.then(data => parseNodes(data.nodes, parentId)).then(nodes => appendNodes(nodes));
  json.then(data => parseEdges(data.edges, parentId)).then(edges => appendEdges(edges));

}
  return (
    <Card className="w-[350px]">
      <CardHeader>
        <CardTitle>Eval</CardTitle>
        <CardDescription>Name: {data.name} </CardDescription>
      </CardHeader>

      <CardContent>

      </CardContent>
      <CardFooter>
        <Button onClick={() => loadChildren(tmpURL, data.id)} >Show</Button>
      </CardFooter>
    
      <Handle type="target" position={Position.Top} />
      <Handle type="source" position={Position.Bottom} />
    </Card>
  );
}
