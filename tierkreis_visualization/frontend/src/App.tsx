import { useSuspenseQuery } from "@tanstack/react-query";
import {
  applyEdgeChanges,
  applyNodeChanges,
  Edge,
  OnEdgesChange,
  OnNodesChange,
  ReactFlow,
  useReactFlow,
  OnNodeDrag,
} from "@xyflow/react";
import { useParams } from "react-router";

import Layout from "@/components/layout";
import { InfoProps, Workflow } from "@/components/types";
import { URL } from "@/data/constants";
import { parseGraph } from "@/graph/parseGraph";
import { Background, ControlButton, Controls } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Network } from "lucide-react";
import React, { useCallback, useState } from "react";

import { SidebarTrigger } from "@/components/ui/sidebar";
import { edgeTypes } from "@/edges";
import { bottomUpLayout } from "@/graph/layoutGraph";
import { nodeTypes } from "@/nodes";
import { BackendNode } from "./nodes/types";

const saveGraph = ({
  key,
  ...graph
}: {
  key: string;
  nodes: BackendNode[];
  edges: Edge[];
  start_time: string;
}) => {
  try {
    localStorage.setItem(key, JSON.stringify(graph));
  } catch {
    return null;
  }
};

const deleteGraph = ({ key }: { key: string }) => {
  try {
    localStorage.removeItem(key);
  } catch {
    return null;
  }
};

const loadGraph = (props: {
  key: string;
}): { nodes: BackendNode[]; edges: Edge[]; start_time: string } | null => {
  try {
    const item = localStorage.getItem(props.key);
    if (item !== null)
      return JSON.parse(item) as {
        nodes: BackendNode[];
        edges: Edge[];
        start_time: string;
      };
    return null;
  } catch {
    return null;
  }
};

const Main = (props: {
  initialNodes: BackendNode[];
  initialEdges: Edge[];
  workflow_id: string;
  workflow_start: string;
  workflows: Workflow[];
  infoProps: InfoProps;
  setInfo: (arg: InfoProps) => void;
}) => {
  // Client node state (not definition)
  const [nodes, setNodes] = useState(props.initialNodes);
  const [edges, setEdges] = useState(props.initialEdges);
  React.useEffect(() => {
    saveGraph({
      key: props.workflow_id,
      nodes,
      edges,
      start_time: props.workflow_start,
    });
  }, [edges, nodes, props.workflow_id, props.workflow_start]);
  const onNodesChange: OnNodesChange<BackendNode> = useCallback(
    (changes) =>
      setNodes((nodesSnapshot) => applyNodeChanges(changes, nodesSnapshot)),
    []
  );
  const onEdgesChange: OnEdgesChange = useCallback(
    (changes) =>
      setEdges((edgesSnapshot) => applyEdgeChanges(changes, edgesSnapshot)),
    []
  );
  const onNodeDrag: OnNodeDrag = useCallback((_, node) => {
    node.data.pinned = true;
  }, []);
  const reactFlowInstance = useReactFlow();
  React.useEffect(() => {
    const url = `${URL}/${props.workflow_id}/nodes/-`;
    const ws = new WebSocket(url);
    const edges = reactFlowInstance.getEdges();
    const nodes = reactFlowInstance.getNodes() as BackendNode[];
    ws.onmessage = (event) => {
      const graph = parseGraph(
        JSON.parse(event.data),
        props.workflow_id,
        props.setInfo
      );
      const nodesMap = new Map(nodes.map((node) => [node.id, node]));
      const newNodes = bottomUpLayout(graph.nodes, graph.edges);
      newNodes.forEach((node) => {
        const existingNode = nodesMap.get(node.id);
        if (existingNode) {
          existingNode.data = {
            ...existingNode.data,
            status: node.data.status,
          };
          existingNode.position = {
            ...(reactFlowInstance.getNode(node.id)?.position ?? node.position),
          };
        } else {
          nodesMap.set(node.id, node);
        }
      });
      setNodes(Array.from(nodesMap.values()));
      const edgeIds = new Set(edges.map((edge) => edge.id));
      const newEdges = graph.edges.filter((edge) => !edgeIds.has(edge.id));
      if (newEdges.length > 0) {
        setEdges([...edges, ...newEdges]);
      }
    };
    return () => {
      if (ws.readyState == WebSocket.OPEN) {
        ws.close();
      }
    };
  }, [props, reactFlowInstance, setNodes, setEdges]);

  return (
    <Layout
      workflows={props.workflows}
      workflowId={props.workflow_id}
      info={props.infoProps}
    >
      <ReactFlow<BackendNode, Edge>
        nodes={nodes}
        edges={edges}
        defaultNodes={nodes}
        defaultEdges={edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        onEdgesChange={onEdgesChange}
        onNodesChange={onNodesChange}
        onNodeDrag={onNodeDrag}
        fitView
      >
        <Background />
        <Controls showZoom={false} showInteractive={false}>
          <SidebarTrigger style={{ fill: "none" }} />
          <ControlButton
            onClick={() => {
              setEdges(edges);
              setNodes(bottomUpLayout(nodes, reactFlowInstance.getEdges()));
              reactFlowInstance.fitView({ padding: 0.1 });
            }}
          >
            <Network style={{ fill: "none" }} />
          </ControlButton>
        </Controls>
      </ReactFlow>
    </Layout>
  );
};

export default function App() {
  const { workflowId: workflow_id_url } = useParams();

  const workflowsQuery = useSuspenseQuery<Workflow[]>({
    queryKey: ["workflows", URL],
    queryFn: async () => {
      const response = await fetch(`${URL}/all`);
      if (!response.ok) {
        throw new Error("Network response was not ok");
      }
      return response.json();
    },
    select: (data) =>
      data.map(
        (workflow): Workflow => ({
          id: workflow.id,
          name: workflow.name,
          start_time: workflow.start_time,
        })
      ),
    staleTime: 1000 * 60 * 5, // Cache for 5 minutes
  });
  const workflow_id = workflow_id_url || workflowsQuery.data[0].id;

  const logs = useSuspenseQuery({
    queryKey: ["workflowLogs", workflow_id],
    queryFn: async () => {
      const url = `${URL}/${workflow_id}/logs`;
      const response = await fetch(url, {
        method: "GET",
        headers: { Accept: "application/text" },
      });
      if (!response.ok) {
        throw new Error("Network response was not ok");
      }
      return response.text();
    },
    staleTime: 1000 * 60 * 5,
  });
  const [info, setInfo] = useState<InfoProps>({
    type: "Logs",
    content: logs.data,
  });

  const graphQuery = useSuspenseQuery({
    queryKey: ["workflowGraph", workflow_id],
    queryFn: async () => {
      const response = await fetch(`${URL}/${workflow_id}/nodes/-`, {
        method: "GET",
        headers: { Accept: "application/json" },
      });
      if (!response.ok) {
        throw new Error("Network response was not ok");
      }
      return response.json();
    },
    select: (data) => parseGraph(data, workflow_id, setInfo),
  });

  const remoteGraph = graphQuery.data;
  const workflow_start = workflowsQuery.data.find(
    (workflow) => workflow.id == workflow_id
  )?.start_time || "";
  const localGraph = loadGraph({ key: workflow_id });
  if (workflow_start && workflow_start != localGraph?.start_time) {
    deleteGraph({ key: workflow_id });
    localGraph == null;
  }

  const mergedGraph = (() => {
    const default_node_positions = bottomUpLayout(
      remoteGraph.nodes,
      remoteGraph.edges
    );
    if (localGraph === null)
      return {
        nodes: default_node_positions,
        edges: remoteGraph.edges,
      };

    const mergedNodes = default_node_positions.map((node) => {
      return {
        ...node,
        position:
          localGraph.nodes.find(
            (oldNode) => oldNode.id === node.id && oldNode.data.pinned
          )?.position ?? node.position,
      };
    });
    const edgesMap = new Map();
    localGraph.edges.forEach((edge) => edgesMap.set(edge.id, edge));
    remoteGraph.edges.forEach((edge) => edgesMap.set(edge.id, edge));
    const mergedEdges = [...edgesMap.values()];

    return {
      nodes: mergedNodes,
      edges: mergedEdges,
    };
  })();

  return (
    <Main
      key={workflow_id}
      initialNodes={mergedGraph.nodes}
      initialEdges={mergedGraph.edges}
      workflows={workflowsQuery.data}
      workflow_id={workflow_id}
      workflow_start={workflow_start}
      infoProps={info}
      setInfo={setInfo}
    />
  );
}
