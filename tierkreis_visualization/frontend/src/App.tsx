import { useShallow } from "zustand/react/shallow";
import { SidebarTrigger } from "@/components/ui/sidebar";
import {
  ReactFlow,
  ReactFlowProvider,
  Background,
  Controls,
  MiniMap,
  ControlButton,
} from "@xyflow/react";
import { RedoDot, UndoDot } from "lucide-react";
import Layout from "@/components/layout";

import useStore from "@/data/store";

const selector = (state) => ({
  nodes: state.nodes,
  edges: state.edges,
  onNodesChange: state.onNodesChange,
  onEdgesChange: state.onEdgesChange,
  onConnect: state.onConnect,
});

import "@xyflow/react/dist/style.css";

import { nodeTypes } from "./nodes";
import { edgeTypes } from "./edges";

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
          <MiniMap />
          <Controls showZoom={false} showInteractive={false}>
            <SidebarTrigger style={{fill: "none"}}/>
            <ControlButton onClick={() => undo()}>
              <UndoDot style={{fill: "none"}}/>
            </ControlButton>
            <ControlButton onClick={() => redo()}>
              <RedoDot style={{fill: "none"}}/>
            </ControlButton>
          </Controls>
        </ReactFlow>
      </ReactFlowProvider>
    </Layout>
  );
}
