import type { Node, BuiltInNode } from '@xyflow/react';

export type InputNode = Node<{ name: string, color: string, outputs: [{ name: string, value: any }] }, 'Input'>;
export type AppNode = BuiltInNode | InputNode;
