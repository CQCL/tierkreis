import {
  Background,
  ControlButton,
  Controls,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { RedoDot, UndoDot } from "lucide-react";
import { useShallow } from "zustand/react/shallow";

import Layout from "@/components/layout";
import { SidebarTrigger } from "@/components/ui/sidebar";
import useStore from "@/data/store";
import { edgeTypes } from "@/edges";
import { nodeTypes } from "@/nodes";
import { AppState } from "@/nodes/types";

const selector = (state: AppState) => ({
  nodes: state.nodes,
  edges: state.edges,
  onNodesChange: state.onNodesChange,
  onEdgesChange: state.onEdgesChange,
  onConnect: state.onConnect,
});

export default function App() {
  const { nodes, edges, onNodesChange, onEdgesChange, onConnect } = useStore(
    useShallow(selector)
  );
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
          fitView
        >
          <Background />
          <Controls showZoom={false} showInteractive={false}>
            <SidebarTrigger style={{ fill: "none" }} />
            <ControlButton onClick={() => undo()}>
              <UndoDot style={{ fill: "none" }} />
            </ControlButton>
            <ControlButton onClick={() => redo()}>
              <RedoDot style={{ fill: "none" }} />
            </ControlButton>
          </Controls>
        </ReactFlow>
      </ReactFlowProvider>
    </Layout>
  );
}
