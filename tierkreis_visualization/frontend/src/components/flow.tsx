import {
  Background,
  ControlButton,
  Controls,
  Edge,
  ReactFlow,
  useReactFlow,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Network } from "lucide-react";

import { SidebarTrigger } from "@/components/ui/sidebar";
import { edgeTypes } from "@/edges";
import { nodeTypes } from "@/nodes";
import { bottomUpLayout } from "@/graph/layoutGraph";
import throttle from "just-throttle";
import { AppNode } from "@/nodes/types";
import { useCallback } from "react";

function save(newState: {
  workflowId: string;
  nodes: AppNode[];
  edges: Edge[];
}) {
  if (
    typeof window !== "undefined" &&
    newState.workflowId != "" &&
    newState.nodes.length > 0
  ) {
    window.localStorage.setItem(newState.workflowId, JSON.stringify(newState));
  }
}

export default function Flow({ workflowId }: { workflowId: string }) {
  const reactFlowInstance = useReactFlow();
  const edges = reactFlowInstance.getEdges();
  const nodes = reactFlowInstance.getNodes();
  const throttledSave = useCallback(
    (workflowId: string) => {
      throttle(() => save({ workflowId, nodes, edges }), 500, {
        leading: true,
      });
    },
    [edges, nodes]
  );

  return (
    <ReactFlow
      defaultNodes={[]}
      defaultEdges={[]}
      nodeTypes={nodeTypes}
      edgeTypes={edgeTypes}
      onNodesChange={() => throttledSave(workflowId)}
      onEdgesChange={() => throttledSave(workflowId)}
      fitView
    >
      <Background />
      <Controls showZoom={false} showInteractive={false}>
        <SidebarTrigger style={{ fill: "none" }} />
        <ControlButton
          onClick={() => {
            const newNodes = bottomUpLayout(nodes, edges);
            reactFlowInstance.setNodes(newNodes);
            reactFlowInstance.setEdges(edges);
            reactFlowInstance.fitView({ padding: 0.1 });
          }}
        >
          <Network style={{ fill: "none" }} />
        </ControlButton>
      </Controls>
    </ReactFlow>
  );
}
