import {
  Background,
  ControlButton,
  Controls,
  ReactFlow,
  ReactFlowProvider,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { RedoDot, UndoDot, Network } from "lucide-react";
import { useShallow } from "zustand/react/shallow";

import Layout from "@/components/layout";
import { SidebarTrigger } from "@/components/ui/sidebar";
import useStore from "@/data/store";
import { edgeTypes } from "@/edges";
import { nodeTypes } from "@/nodes";
import { AppState } from "@/nodes/types";
import { stat } from "fs";

const selector = (state: AppState) => ({
  nodes: state.nodes,
  edges: state.edges,
  onNodesChange: state.onNodesChange,
  onEdgesChange: state.onEdgesChange,
  onConnect: state.onConnect,
  recalculateNodePositions: state.recalculateNodePositions,
});

export default function App() {
  const {
    nodes,
    edges,
    onNodesChange,
    onEdgesChange,
    onConnect,
    recalculateNodePositions,
  } = useStore(useShallow(selector));
  const { undo, redo } = useStore.temporal.getState();
  return (
    <Layout>
      <ReactFlowProvider>
        <ReactFlow
          nodes={nodes}
          nodeTypes={nodeTypes}
          onNodesChange={onNodesChange}
          edges={edges}
          edgeTypes={edgeTypes}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          // minZoom={0.001}
          // maxZoom={10}
          fitView
        >
          <Background />
          <Controls showZoom={false} showInteractive={false}>
            <SidebarTrigger style={{ fill: "none" }} />
            {/* <ControlButton onClick={() => undo(2)}>
              <UndoDot style={{ fill: "none" }} />
            </ControlButton>
            <ControlButton onClick={() => redo(2)}>
              <RedoDot style={{ fill: "none" }} />
            </ControlButton> */}
            <ControlButton onClick={() => recalculateNodePositions()}>
              <Network style={{ fill: "none" }} />
            </ControlButton>
          </Controls>
        </ReactFlow>
      </ReactFlowProvider>
    </Layout>
  );
}
