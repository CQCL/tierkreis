import {useSuspenseQuery} from "@tanstack/react-query";
import {
  applyEdgeChanges,
  applyNodeChanges,
  Edge,
  OnEdgesChange,
  OnNodesChange,
  ReactFlow,
  useReactFlow,
} from "@xyflow/react";
import {useParams} from "react-router";

import Layout from "@/components/layout";
import {Workflow} from "@/components/types";
import {URL} from "@/data/constants";
import {parseGraph} from "@/graph/parseGraph";
import {Background, ControlButton, Controls} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import {Network} from "lucide-react";
import React, {useCallback, useState} from "react";

import {SidebarTrigger} from "@/components/ui/sidebar";
import {edgeTypes} from "@/edges";
import {bottomUpLayout} from "@/graph/layoutGraph";
import {nodeTypes} from "@/nodes";
import {BackendNode} from "./nodes/types";
// function fromStorage(workflow_id: string): PartialState {
//   const storedData = localStorage.getItem(workflow_id);
//   try {
//     return JSON.parse(storedData || "{}") as PartialState;
//   } catch (error) {
//     return { workflow_id: "", nodes: [], edges: [] } as PartialState;
//   }
// }

const saveGraph = ({
  key,
  ...graph
}: {
  key: string;
  nodes: BackendNode[];
  edges: Edge[];
}) => {
  try {
    localStorage.setItem(key, JSON.stringify(graph));
  } catch {
    return null;
  }
};

const loadGraph = (props: {
  key: string;
}): {nodes: BackendNode[]; edges: Edge[]} | null => {
  try {
    const item = localStorage.getItem(props.key);
    if (item !== null)
      return JSON.parse(item) as {nodes: BackendNode[]; edges: Edge[]};
    return null;
  } catch {
    return null;
  }
};

const Main = (props: {
  initialNodes: BackendNode[];
  initialEdges: Edge[];
  workflow_id: string;
  workflows: Workflow[];
}) => {
  // Client node state (not definition)
  const [nodes, setNodes] = useState(props.initialNodes);
  const [edges, setEdges] = useState(props.initialEdges);

  React.useEffect(() => {
    saveGraph({key: props.workflow_id, nodes, edges});
  }, [edges, nodes, props.workflow_id]);

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

  const reactFlowInstance = useReactFlow();

  return (
    <Layout workflows={props.workflows} workflowId={props.workflow_id}>
      <ReactFlow<BackendNode, Edge>
        defaultNodes={nodes}
        defaultEdges={edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        onEdgesChange={onEdgesChange}
        onNodesChange={onNodesChange}
        fitView
      >
        <Background />
        <Controls showZoom={false} showInteractive={false}>
          <SidebarTrigger style={{fill: "none"}} />
          <ControlButton
            onClick={() => {
              setNodes(bottomUpLayout(nodes, edges));
              setEdges(edges);
              reactFlowInstance.fitView({padding: 0.1});
            }}
          >
            <Network style={{fill: "none"}} />
          </ControlButton>
        </Controls>
      </ReactFlow>
    </Layout>
  );
};

export default function App() {
  const {workflowId: workflow_id_url} = useParams();

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
        })
      ),
    staleTime: 1000 * 60 * 5, // Cache for 5 minutes
  });
  const workflow_id = workflow_id_url || workflowsQuery.data[0].id;
  const graphQuery = useSuspenseQuery({
    queryKey: ["workflowGraph", workflow_id],
    queryFn: async () => {
      const response = await fetch(`${URL}/${workflow_id}/nodes/-`, {
        method: "GET",
        headers: {Accept: "application/json"},
      });
      if (!response.ok) {
        throw new Error("Network response was not ok");
      }
      return response.json();
    },
    select: (data) => parseGraph(data, workflow_id),
  });

  const remoteGraph = graphQuery.data;
  const localGraph = loadGraph({key: workflow_id});
  // console.log(remoteGraph, localGraph)

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
          localGraph.nodes.find((oldNode) => oldNode.id === node.id)
            ?.position || node.position,
      };
    });
    const edgesMap = new Map();
    localGraph.edges.forEach((edge) => edgesMap.set(edge.id, edge));
    localGraph.edges.forEach((edge) => edgesMap.set(edge.id, edge));
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
    />
  );
}
