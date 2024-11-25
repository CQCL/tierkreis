// rexport for encoding in other workspace crates
pub use prost::Message;

use crate::protos_gen::v1alpha1::controller as pc;
use crate::ConvertError;
use std::fmt::Display;
use std::str::FromStr;
use thiserror::Error;
use tierkreis_core::graph::NodeIndex;
use tierkreis_core::prelude::TryFrom;

#[derive(Debug, Clone, PartialEq)]

/// A stack trace identifying a node
pub struct NodeTrace {
    /// Index of the node.
    node: NodeIndex,
    /// Identifies the graph execution of which this node is part
    graph_trace: Box<GraphTrace>,
}

impl NodeTrace {
    /// Creates a trace of the specified node in the specified graph trace
    pub fn new(node: NodeIndex, graph_trace: GraphTrace) -> Self {
        Self {
            node,
            graph_trace: Box::new(graph_trace),
        }
    }

    /// Append a node to the trace.
    pub fn inner_node(self, node: NodeIndex) -> Self {
        let graph_t: GraphTrace = self.into();
        graph_t.inner_node(node)
    }

    /// Append a loop iteration to the stack trace.
    pub fn loop_iter(self, iter: u32) -> GraphTrace {
        GraphTrace::Loop {
            iter,
            parent_node: self,
        }
    }

    /// Append a list element to the stack trace.
    pub fn list_elem(self, idx: u32) -> GraphTrace {
        GraphTrace::Map {
            idx,
            parent_node: self,
        }
    }

    /// Encode to bytes via conversion to [`pc::NodeId`]
    pub fn into_bytes(self) -> Vec<u8> {
        let node_id: pc::NodeId = self.into();
        node_id.encode_to_vec()
    }
}

#[derive(Debug, Clone, PartialEq, Default)]
/// A nested stack trace, with variants corresponding to the type of the
/// innermost frame in the stack.
pub enum GraphTrace {
    #[default]
    /// Outermost scope of a job/run_graph request.
    Root,
    /// Stack trace ending in a node (a `Box` or `eval`)
    Node(NodeTrace),
    /// Stack trace ending in a loop iteration.
    Loop {
        /// Count of loop iterations
        iter: u32,
        /// The `loop` node
        parent_node: NodeTrace,
    },
    /// Stack trace ending in a list element inside a `map` node.
    Map {
        /// Index of element in the list (`value`) argument
        /// for which the graph was being evaluated
        idx: u32,
        /// The `map` node evaluating the graph
        parent_node: NodeTrace,
    },
}

#[derive(Debug, Error)]
#[error("GraphTrace does not correspond to a Node.")]
pub struct NotNodeError;

impl From<NodeTrace> for GraphTrace {
    fn from(value: NodeTrace) -> Self {
        Self::Node(value)
    }
}

impl GraphTrace {
    /// Append a node to the stack trace.
    pub fn inner_node(self, node: NodeIndex) -> NodeTrace {
        NodeTrace {
            node,
            graph_trace: Box::new(self),
        }
    }

    /// For Graphs executing due to evaluating a `Box` or `eval` node,
    /// the trace of the node. (`Err` if a `loop`, `map` or the root graph.)
    pub fn as_node_trace(self) -> Result<NodeTrace, NotNodeError> {
        if let GraphTrace::Node(nt) = self {
            Ok(nt)
        } else {
            Err(NotNodeError)
        }
    }

    /// Convert the stack trace to a list of strings for encoding.
    fn into_strings(self) -> Vec<String> {
        let mut graph_trace = self;
        let mut prefix_strings = vec![];
        loop {
            match graph_trace {
                GraphTrace::Root => break,
                GraphTrace::Node(NodeTrace {
                    node,
                    graph_trace: parent_trace,
                }) => {
                    prefix_strings.push(format!("N{}", node.index()));
                    graph_trace = *parent_trace;
                }
                GraphTrace::Loop { iter, parent_node } => {
                    prefix_strings.push(format!("L{}", iter));
                    graph_trace = GraphTrace::Node(parent_node)
                }
                GraphTrace::Map { idx, parent_node } => {
                    prefix_strings.push(format!("M{}", idx));
                    graph_trace = GraphTrace::Node(parent_node)
                }
            }
        }
        prefix_strings.reverse();
        prefix_strings
    }

    /// Decode a stack trace from a list of strings.
    fn from_strings(prefix_strings: Vec<String>) -> Result<Self, ConvertError> {
        fn parse_s<T: FromStr>(s: &str) -> Result<T, ConvertError> {
            s.parse().map_err(|_| ConvertError::ProtoError)
        }
        let mut graph_trace = GraphTrace::Root;

        for mut s in prefix_strings {
            if s.is_empty() {
                return Err(ConvertError::ProtoError);
            }
            match s.remove(0) {
                'N' => {
                    graph_trace = graph_trace.inner_node(NodeIndex::new(parse_s(&s)?)).into();
                }
                'L' => {
                    graph_trace = graph_trace.as_node_trace()?.loop_iter(parse_s(&s)?);
                }
                'M' => {
                    graph_trace = graph_trace.as_node_trace()?.list_elem(parse_s(&s)?);
                }
                _ => return Err(ConvertError::ProtoError),
            }
        }

        Ok(graph_trace)
    }
}

impl Display for GraphTrace {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        // join the strings with a dot
        f.write_str(&self.clone().into_strings().join("."))
    }
}

impl Display for NodeTrace {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}.N{}", self.graph_trace, self.node.index())
    }
}

impl From<NodeTrace> for pc::NodeId {
    fn from(value: NodeTrace) -> Self {
        let NodeTrace { graph_trace, node } = value;
        let node_index = node.index() as u32;

        Self {
            node_index,
            prefix: (*graph_trace).into_strings(),
        }
    }
}

impl From<NotNodeError> for ConvertError {
    fn from(_: NotNodeError) -> Self {
        ConvertError::InvalidNodeId
    }
}

impl TryFrom<pc::NodeId> for NodeTrace {
    type Error = ConvertError;

    fn try_from(value: pc::NodeId) -> Result<Self, Self::Error> {
        let node = NodeIndex::new(value.node_index as usize);

        let graph_trace = GraphTrace::from_strings(value.prefix)?;

        Ok(NodeTrace {
            graph_trace: Box::new(graph_trace),
            node,
        })
    }
}

#[cfg(test)]
mod test {
    use super::*;
    use rstest::rstest;

    #[test]
    fn trace_convert_both_ways() {
        let node_id = pc::NodeId {
            node_index: 17,
            prefix: to_vec_str(&["N0", "L1", "N23", "N7", "M2", "N34435"]),
        };

        let stack_trace = <NodeTrace as TryFrom<_>>::try_from(node_id.clone()).unwrap();
        assert_eq!(
            stack_trace,
            NodeTrace {
                node: 17.into(),
                graph_trace: Box::new(
                    GraphTrace::Root
                        .inner_node(0.into())
                        .loop_iter(1)
                        .inner_node(23.into())
                        .inner_node(7.into())
                        .list_elem(2)
                        .inner_node(34435.into())
                        .into()
                )
            }
        );

        assert_eq!(
            stack_trace.graph_trace.to_string(),
            "N0.L1.N23.N7.M2.N34435"
        );
        let new_node_id: pc::NodeId = stack_trace.into();
        assert_eq!(new_node_id, node_id);
    }

    #[test]
    fn empty_prefix() {
        let node_id = pc::NodeId {
            node_index: 17,
            prefix: vec![],
        };

        let stack_trace = <NodeTrace as TryFrom<_>>::try_from(node_id.clone()).unwrap();

        assert_eq!(
            stack_trace,
            NodeTrace {
                graph_trace: GraphTrace::Root.into(),
                node: NodeIndex::new(17),
            }
        );

        let new_node_id: pc::NodeId = stack_trace.into();
        assert_eq!(new_node_id, node_id);
    }

    // convert array of &str to Vec<String>
    fn to_vec_str(arr: &[&str]) -> Vec<String> {
        arr.iter().map(|x| x.to_string()).collect()
    }

    #[rstest]
    #[case(&["N0"])]
    #[case(&["N0", "M1"])]
    #[case(&["N0", "M1", "N2", "N3", "L4"])]
    #[case(&["N0", "M1", "N2", "N3", "L4", "N3"])]
    fn valid_roundtrip(#[case] prefix: &[&str]) {
        let node_id = pc::NodeId {
            node_index: 17,
            prefix: to_vec_str(prefix),
        };

        let node_trace = <NodeTrace as TryFrom<_>>::try_from(node_id.clone()).unwrap();

        let new_node_id: pc::NodeId = node_trace.into();

        assert_eq!(new_node_id, node_id);
    }

    #[rstest]
    #[case(&["L0"])]
    #[case(&["L0", "M1"])]
    #[case(&["M0", "M1"])]
    #[case(&["M0"])]
    #[case(&["L1", "N1"])]
    #[case(&["N1", "M3", "L4"])]
    #[case(&["N1", "N1.3"])]
    #[case(&["N1", "M-1"])]
    #[case(&["word"])]
    fn invalid_prefixes(#[case] prefix: &[&str]) {
        let node_id = pc::NodeId {
            node_index: 17,
            prefix: to_vec_str(prefix),
        };

        let node_trace_res = <NodeTrace as TryFrom<_>>::try_from(node_id);
        assert!(node_trace_res.is_err());
    }
}
