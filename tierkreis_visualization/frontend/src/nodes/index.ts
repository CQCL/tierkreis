import type { NodeTypes } from '@xyflow/react';

import { AppNode } from './types';
import { parseNodes } from './parseNodes';
import { workflowId, nodeName, url } from '../data/constants';

export const initialNodes: AppNode[] = await fetch(`${url}/${workflowId}/nodes/${nodeName}`, { method: 'GET', headers: { 'Accept': 'application/json' } })
  .then(response => response.json())
  .then(data => parseNodes(data));

export const nodeTypes = {
  // Add any of your custom nodes here!
} satisfies NodeTypes;
