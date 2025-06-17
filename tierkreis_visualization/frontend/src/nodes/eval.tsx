import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { type NodeProps } from "@xyflow/react";
import { useShallow } from "zustand/react/shallow";

import { InputHandleArray, OutputHandleArray } from "@/components/handles";
import { NodeStatusIndicator } from "@/components/StatusIndicator";
import { Button } from "@/components/ui/button";
import { URL } from "@/data/constants";
import useStore from "@/data/store";
import { parseEdges, parseNodes } from "@/graph/parseGraph";
import { AppState, type BackendNode } from "./types";

const selector = (state: AppState) => ({
  replaceEval: state.replaceEval,
  recalculateNodePositions: state.recalculateNodePositions,
});

export function EvalNode({ data }: NodeProps<BackendNode>) {
  const { replaceEval, recalculateNodePositions } = useStore(
    useShallow(selector)
  );
  const loadChildren = async (
    workflowId: string,
    node_location: string,
    parentId: string
  ) => {
    const url = `${URL}/${workflowId}/nodes/${node_location}`;
    fetch(url, { method: "GET", headers: { Accept: "application/json" } })
      .then((response) => response.json())
      .then((data) => {
        const nodes = parseNodes(data.nodes, data.edges, workflowId, parentId);
        const edges = parseEdges(data.edges, parentId);
        replaceEval(parentId, nodes, edges);
      })
      .then(() => {
        recalculateNodePositions();
      });
  };
  return (
    <NodeStatusIndicator status={data.status}>
      <Card className="w-[350px]">
        <CardHeader>
          <CardTitle>{data.title}</CardTitle>
          <CardDescription>Name: {data.name} </CardDescription>
        </CardHeader>

        <CardContent>
          <InputHandleArray handles={data.handles.inputs} id={data.id} />
          <OutputHandleArray handles={data.handles.outputs} id={data.id} />
        </CardContent>
        <CardFooter>
          <Button
            onClick={() =>
              loadChildren(data.workflowId, data.node_location, data.id)
            }
          >
            Show
          </Button>
        </CardFooter>
      </Card>
    </NodeStatusIndicator>
  );
}
