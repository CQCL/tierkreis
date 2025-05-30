import type { NodeTypes } from '@xyflow/react';

import { ConstNode } from './const';
import { EvalNode } from './eval';
import { InputNode }   from './input';
import { OutputNode } from './output';
import { AppNode } from './types';

export const initialNodes = [] as AppNode[];

export const nodeTypes = {
  "input-node": InputNode,
  "const-node": ConstNode,
  "output-node": OutputNode,
  "eval-node": EvalNode,
} satisfies NodeTypes;
