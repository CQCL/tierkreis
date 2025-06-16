import { useShallow } from "zustand/react/shallow";
import { type NodeProps } from "@xyflow/react";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

import { Button } from "@/components/ui/button";
import { NodeStatusIndicator } from "@/components/StatusIndicator";
import useStore from "@/data/store";
import { parseNodes } from "@/graph/parseGraph";
import { InputHandleArray, OutputHandleArray } from "@/components/handles";
import { type BackendNode } from "./types";
import { URL } from "@/data/constants";

const selector = (state) => ({
  replaceMap: state.replaceMap,
  recalculateNodePositions: state.recalculateNodePositions,
});

export function MapNode({ data }: NodeProps<BackendNode>) {
  const { replaceMap, recalculateNodePositions } = useStore(
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
      .then((data) => parseNodes(data.nodes, data.edges, workflowId, parentId))
      .then((nodes) => replaceMap(parentId, nodes))
      .then(() => {
        recalculateNodePositions();
      });
    //no need to parse edges, they are always [] for map
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
