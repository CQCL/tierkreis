import type { Node, BuiltInNode } from '@xyflow/react';

export type PyNode = { id: string | number ; status: "Not started" | "Started" | "Error" | "Finished"; function_name: string };
export type BackendNode = Node<{ name: string, status: "Started" | "Finished" | "Error" | "Not Started", outputs: [{ name: string, value: any }] }, 'Input'>;
export type AppNode = BuiltInNode | BackendNode;
