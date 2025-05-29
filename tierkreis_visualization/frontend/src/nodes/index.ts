import type { NodeTypes } from '@xyflow/react';

import { ConstNode } from './const';
import { EvalNode } from './eval';
import { InputNode }   from './input';
import { OutputNode } from './output';
import { AppNode } from './types';
import { parseNodes } from './parseNodes';
import { workflowId, nodeName, url } from '../data/constants';

export const initialNodes: AppNode[] = await fetch(`${url}/${workflowId}/nodes/${nodeName}`, { method: 'GET', headers: { 'Accept': 'application/json' } })
  .then(response => response.json())
  .then(data => parseNodes(data));

export const nodeTypes = {
  "input-node": InputNode,
  "const-node": ConstNode,
  "output-node": OutputNode,
  "eval-node": EvalNode,
} satisfies NodeTypes;
