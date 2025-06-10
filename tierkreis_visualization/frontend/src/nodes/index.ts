import type { NodeTypes } from '@xyflow/react';

import { DefaultNode } from './default';
import { EvalNode } from './eval';
import { FunctionNode } from './function';
import { LoopNode } from './Loop';
import { MapNode } from './map';
import { AppNode } from './types';

export const initialNodes = [] as AppNode[];

export const nodeTypes = {
  "eval-node": EvalNode,
  "function-node": FunctionNode,
  "loop-node": LoopNode,
  "map-node": MapNode,
  "default-node": DefaultNode,
} satisfies NodeTypes;
