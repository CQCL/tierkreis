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
import { parseNodes } from "@/graph/parseGraph";
import { AppState, type BackendNode } from "@/nodes/types";
import { Plus } from "lucide-react";
const selector = (state: AppState) => ({
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
      .then(() => recalculateNodePositions());
  };
  return (
    <NodeStatusIndicator status={data.status}>
      <Card className="w-[180px]">
        <CardHeader>
          <CardTitle>{data.title}</CardTitle>
        </CardHeader>

        <CardContent>
          <div className="flex items-center justify-center">
            <Button
              variant="secondary"
              size="icon"
              onClick={() =>
                loadChildren(data.workflowId, data.node_location, data.id)
              }
            >
              <Plus />
            </Button>
          </div>
          <InputHandleArray handles={data.handles.inputs} id={data.id} />
          <OutputHandleArray handles={data.handles.outputs} id={data.id} />
        </CardContent>
      </Card>
    </NodeStatusIndicator>
  );
}
