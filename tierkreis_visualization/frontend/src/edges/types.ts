export type PyEdge = {
  id: string | number;
  from_node: string | number;
  to_node: string | number;
  from_port: string;
  to_port: string;
  value?: unknown;
};
