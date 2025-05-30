import type { NodeTypes } from '@xyflow/react';

import { ConstNode } from './const';
import { EvalNode } from './eval';
import { FunctionNode } from './function';
import { InputNode } from './input';
import { IfElseNode } from './ifelse';
import { LoopNode } from './Loop';
import { MapNode } from './map';
import { OutputNode } from './output';
import { AppNode } from './types';

export const initialNodes = [] as AppNode[];

export const nodeTypes = {
  "input-node": InputNode,
  "const-node": ConstNode,
  "output-node": OutputNode,
  "eval-node": EvalNode,
  "function-node": FunctionNode,
  "loop-node": LoopNode,
  "map-node": MapNode,
  "ifelse-node": IfElseNode,
} satisfies NodeTypes;
