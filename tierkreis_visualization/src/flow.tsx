import { useEffect, useMemo, useRef } from 'react';
import {
    ReactFlow, Controls, Background, Panel,
    useNodesState,
    useEdgesState,
    useReactFlow,
    useNodesInitialized,
    ReactFlowProvider,
} from '@xyflow/react';
import {
    forceSimulation,
    forceLink,
    forceManyBody,
    forceX,
    forceY,
} from 'd3-force';
import { initialNodes, initialEdges, parse_edges, parse_nodes } from './initial_nodes.js';
import '@xyflow/react/dist/style.css';
import { collide } from './collide.js';


const workflowId = "00000000-0000-0000-0000-000000000066";

const simulation = forceSimulation()
    .force('charge', forceManyBody().strength(-1000))
    .force('x', forceX().x(0).strength(0.05))
    .force('y', forceY().y(0).strength(0.05))
    .force('collide', collide())
    .alphaTarget(0.05)
    .stop();

const useLayoutedElements = () => {
    const { getNodes, setNodes, getEdges, fitView } = useReactFlow();
    const initialized = useNodesInitialized();

    // You can use these events if you want the flow to remain interactive while
    // the simulation is running. The simulation is typically responsible for setting
    // the position of nodes, but if we have a reference to the node being dragged,
    // we use that position instead.
    const draggingNodeRef = useRef(null);
    const dragEvents = useMemo(
        () => ({
            start: (_event, node) => (draggingNodeRef.current = node),
            drag: (_event, node) => (draggingNodeRef.current = node),
            stop: () => (draggingNodeRef.current = null),
        }),
        [],
    );

    return useMemo(() => {
        let nodes = getNodes().map((node) => ({
            ...node,
            x: node.position.x,
            y: node.position.y,
        }));
        let edges = getEdges().map((edge) => edge);
        let running = false;

        // If React Flow hasn't initialized our nodes with a width and height yet, or
        // if there are no nodes in the flow, then we can't run the simulation!
        if (!initialized || nodes.length === 0) return [false, {}, dragEvents];

        simulation.nodes(nodes).force(
            'link',
            forceLink(edges)
                .id((d) => d.id)
                .strength(0.05)
                .distance(100),
        );

        // The tick function is called every animation frame while the simulation is
        // running and progresses the simulation one step forward each time.
        const tick = () => {
            getNodes().forEach((node, i) => {
                const dragging = draggingNodeRef.current?.id === node.id;

                // Setting the fx/fy properties of a node tells the simulation to "fix"
                // the node at that position and ignore any forces that would normally
                // cause it to move.
                if (dragging) {
                    nodes[i].fx = draggingNodeRef.current.position.x;
                    nodes[i].fy = draggingNodeRef.current.position.y;
                } else {
                    delete nodes[i].fx;
                    delete nodes[i].fy;
                }
            });

            simulation.tick();
            setNodes(
                nodes.map((node) => ({
                    ...node,
                    position: { x: node.fx ?? node.x, y: node.fy ?? node.y },
                })),
            );

            window.requestAnimationFrame(() => {
                // Give React and React Flow a chance to update and render the new node
                // positions before we fit the viewport to the new layout.
                fitView();

                // If the simulation hasn't been stopped, schedule another tick.
                if (running) tick();
            });
        };

        const toggle = () => {
            if (!running) {
                getNodes().forEach((node, index) => {
                    let simNode = nodes[index];
                    Object.assign(simNode, node);
                    simNode.x = node.position.x;
                    simNode.y = node.position.y;
                });
            }
            running = !running;
            running && window.requestAnimationFrame(tick);
        };

        const isRunning = () => running;

        return [true, { toggle, isRunning }, dragEvents];
    }, [initialized, dragEvents, getNodes, getEdges, setNodes, fitView]);
};




// Function to handle new nodes being added to the stream

function Flow() {
    const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
    const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
    const [initialized, { toggle, isRunning }, dragEvents] =
        useLayoutedElements();

    useEffect(() => {
        const wsUrl = `ws://localhost:8000/workflows/${workflowId}/nodes/-`;
        const ws = new WebSocket(wsUrl);
        function onMessage(event) {
            console.log("onMessage");
            const data = JSON.parse(event.data);
            console.log(data);
            setNodes(parse_nodes(event.nodes));
            setEdges(parse_edges(event.edges));
        }

        ws.onmessage = onMessage;
        return () => {
            ws.close();
        };
    }, [setNodes]);

    return (
        <div style={{ height: '100%' }}>
            <ReactFlow nodes={nodes} edges={edges}
                onNodeDrag={dragEvents.drag}
                onNodeDragStop={dragEvents.stop}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}>
                <Background />
                <Controls />
                <Panel>
                    {initialized && (
                        <button onClick={toggle}>
                            {isRunning() ? 'Stop' : 'Start'} force simulation
                        </button>
                    )}
                </Panel>
            </ReactFlow>
        </div>
    );
}

export function App() {
    return (
        <ReactFlowProvider>
            <Flow />
        </ReactFlowProvider>
    );
}
