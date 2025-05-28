import type { Edge, EdgeTypes } from '@xyflow/react';
import { parseEdges } from './parseEdges';
import { workflowId, nodeName, url } from '../data/constants';

export const initialEdges: Edge[] =  await fetch(`${url}/${workflowId}/nodes/${nodeName}`, { method: 'GET', headers: { 'Accept': 'application/json' } })
    .then(response => response.json())
    .then(data => parseEdges(data));
export const edgeTypes = {
  // Add your custom edge types here!
} satisfies EdgeTypes;
