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
import { NodeStatusIndicator } from '@/components/StatusIndicator';
import useStore from "@/data/store";
import { parseNodes, parseEdges } from "@/graph/parseGraph";
import { InputHandleArray, OutputHandleArray } from '@/components/handles';
import { type BackendNode } from './types';
import { URL } from '@/data/constants';



export function EvalNode({
  data,
}: NodeProps<BackendNode>) {
  const appendEdges = useStore((state) => state.appendEdges);
  const replaceNode = useStore((state) => state.replaceNode);
  const recalculateNodePositions = useStore((state) => state.recalculateNodePositions);
  const loadChildren = async (workflowId: string, node_location: string, parentId: string) => {
    const url = `${URL}/${workflowId}/nodes/${node_location}`;
    let json = fetch(url, { method: 'GET', headers: { 'Accept': 'application/json' } })
      .then(response => response.json());
    await json.then(data => parseNodes(data.nodes,data.edges, workflowId, parentId)).then(nodes => replaceNode(parentId, nodes));
    await json.then(data => parseEdges(data.edges, parentId)).then(edges => appendEdges(edges));
    
    recalculateNodePositions();
  }
  return (
    <NodeStatusIndicator status={data.status}>
      <Card className="w-[350px]">
        <CardHeader>
          <CardTitle>Eval</CardTitle>
          <CardDescription>Name: {data.name} </CardDescription>
        </CardHeader>

        <CardContent>
          <InputHandleArray handles={data.handles.inputs} id={data.id} />
          <OutputHandleArray handles={data.handles.outputs} id={data.id} />
        </CardContent>
        <CardFooter>
          <Button onClick={() => loadChildren(data.workflowId, data.node_location, data.id)} >Show</Button>
        </CardFooter>
      </Card>
    </NodeStatusIndicator>
  );
}
