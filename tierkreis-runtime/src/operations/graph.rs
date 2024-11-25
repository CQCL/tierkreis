use super::{Input, OperationInputs, Output};
use crate::operations::{OperationContext, RuntimeOperation};
use crate::Location;
use futures::stream::{BoxStream, SelectAll};
use futures::StreamExt;

use std::collections::HashMap;
use std::sync::Arc;
use thiserror::Error;
use tierkreis_core::graph::{Edge, Node, NodeIndex};
use tierkreis_core::graph::{Graph, NodePort, Value};
use tierkreis_core::symbol::FunctionName;
use tierkreis_core::symbol::Label;
use tierkreis_core::type_checker::{value_as_type, TypeErrors};

use tokio::sync::mpsc;
use tokio_stream::wrappers::UnboundedReceiverStream;
use tracing::{instrument, Level};
pub mod checkpoint_client;
enum Event {
    Input(Input),
    Closed,
    NodeOutput(NodeIndex, Output),
}

/// Operation that oversees the execution of a graph.
///
/// This operation spawns an operation for every node in the graph. It then signals to a node when
/// a value is available at one of its input ports. In turn the node operations notify the graph
/// once they produce a value at an output port; the graph then sends the received value along the
/// edge connected to that output port to make it available to the next node or as an output of the
/// graph.
pub(crate) struct GraphOperation {
    graph: Graph,
    context: OperationContext,

    /// Stream of inputs for the graph operation.
    inputs: OperationInputs,

    /// Senders to communicate with the operations of the nodes that are still running.
    /// When a node finishes processing, its sender is removed from this map and graph
    /// execution finishes once this map is empty.
    node_inputs: HashMap<NodeIndex, mpsc::UnboundedSender<Input>>,

    /// Stream over `Event::NodeOutput` events that combines all the output streams of
    /// the graph's nodes.
    node_outputs: SelectAll<BoxStream<'static, Event>>,

    /// Set of edges that have received a value. Key is present if the edge has
    /// ever received a value, and the value is `Some` from the the time the value
    /// is received until the runtime has detected completion of the source node.
    processed_edges: HashMap<(NodePort, NodePort), Option<Value>>,

    /// Retry times for function nodes that have non-default values.
    node_retry_secs: HashMap<NodeIndex, u32>,
}

async fn forward_outputs(
    mut context: OperationContext,
    mut inputs: OperationInputs,
) -> anyhow::Result<()> {
    while let Some(input) = inputs.next().await {
        match input {
            Input::Input { port, value } => {
                if let Some(ch) = context.outer_graph_checkpoint() {
                    ch.record_graph_output(port, value).await;
                } else {
                    context.set_output(port, value)
                }
            }
            Input::Complete => return Ok(()),
        };
    }
    anyhow::bail!("Doesn't happen")
}

impl GraphOperation {
    pub fn new(graph: Graph, context: OperationContext, inputs: OperationInputs) -> Self {
        GraphOperation {
            graph,
            context,
            inputs,
            node_inputs: HashMap::new(),
            node_outputs: SelectAll::new(),
            processed_edges: HashMap::new(),
            node_retry_secs: HashMap::new(),
        }
    }

    /// Starts the operations for all the graph's nodes.
    #[instrument(level = "debug", name = "starting node operations", skip(self))]
    fn start_nodes(&mut self) -> Result<Vec<NodeIndex>, GraphError> {
        let mut node_operations: HashMap<NodeIndex, RuntimeOperation> = HashMap::new();
        let mut started_nodes = Vec::new();
        for node_idx in self.graph.node_indices() {
            let node = self.graph.node(node_idx).expect("Node should exist.");
            let operation = match node {
                Node::Input => continue,
                Node::Output => {
                    let ctx = self.context.clone();
                    RuntimeOperation::new(move |_ctx, inputs| forward_outputs(ctx, inputs))
                }
                Node::Const(value) => RuntimeOperation::new_const(value.clone()),
                Node::Box(loc, graph) => RuntimeOperation::new_box(loc.clone(), graph.clone()),
                Node::Function(function, retry) => {
                    if let Some(retry_secs) = retry {
                        self.node_retry_secs.insert(node_idx, *retry_secs);
                    }
                    self.context
                        .runtime
                        .run_function_with_loc(function, &Location::local())
                        // If function name is not recognized, try the escape hatch.
                        // callback - yes, if the "escape hatch" runs a function on a worker that's inaccessible to us,
                        // that worker will get our callback. TODO that means it must be able to access the callback -
                        // really we should forward the entire chain of calls from worker, up to escape hatch (root),
                        // back down to this runtime, then back up to the callback (closest enclosing scope).
                        // Ugh. Maybe we should pass a null callback here??
                        .or_else(|| self.context.escape.spawn_escape(function.clone()))
                        .ok_or_else(|| GraphError::UnknownFunction(node_idx, function.clone()))?
                }
                Node::Match => RuntimeOperation::new_match(),
                Node::Tag(tag) => RuntimeOperation::new_tag(*tag),
            };

            node_operations.insert(node_idx, operation);
        }

        for (node_idx, operation) in node_operations {
            self.start_node(node_idx, operation);
            started_nodes.push(node_idx);
        }

        Ok(started_nodes)
    }

    /// Starts a node's operation.
    ///
    /// If the node does not have any input edges, the node is notified of the completion of its
    /// inputs immediately.
    #[instrument(
        level = "debug",
        name = "graph node",
        skip(self, node, operation),
        fields(tierkreis.node = node.index())
    )]
    fn start_node(&mut self, node: NodeIndex, operation: RuntimeOperation) {
        let (inputs_tx, inputs_rx) = mpsc::unbounded_channel();

        self.node_inputs.insert(node, inputs_tx.clone());

        let node_trace = self.context.graph_trace.clone().inner_node(node);

        let outputs = operation.run(
            self.context.runtime.clone(),
            self.context.callback.clone(),
            self.context.escape.clone(),
            UnboundedReceiverStream::new(inputs_rx),
            node_trace.into(),
            self.context.checkpoint_client.clone(),
        );

        self.node_outputs.push(
            outputs
                .map(move |output| Event::NodeOutput(node, output))
                .boxed(),
        );
    }

    #[instrument(name = "graph operation", skip(self), level = "debug")]
    pub async fn run(mut self) -> anyhow::Result<()> {
        let started_nodes = self.start_nodes()?;
        for node in started_nodes {
            // Note this does not include the Input
            self.check_inputs_complete(node).await;
        }
        loop {
            let event = tokio::select! {
                msg = self.inputs.next() => {
                    match msg {
                        Some(input) => Event::Input(input),
                        None => Event::Closed,
                    }
                }
                Some(event) = self.node_outputs.next() => event,
            };

            match event {
                Event::Input(Input::Input { port, value }) => {
                    tracing::debug!(
                        tierkreis.port = port.as_ref(),
                        "received value on input port",
                    );

                    let source = NodePort {
                        node: Graph::boundary()[0],
                        port,
                    };

                    self.set_edge_value(source, value)?;
                    self.check_target_complete(source).await;
                }

                Event::Input(Input::Complete) => {
                    if self.node_inputs.is_empty() {
                        return Ok(());
                    }
                }

                Event::Closed => {
                    tracing::warn!("cancelled graph execution because input stream closed");
                    return Ok(());
                }

                Event::NodeOutput(node, Output::Output { port, value }) => {
                    tracing::debug!(
                        tierkreis.node = node.index(),
                        tierkreis.port = port.as_ref(),
                        "node produced value on output port",
                    );

                    let source = NodePort { node, port };

                    self.set_edge_value(source, value)?;
                    self.check_target_complete(source).await;
                }

                Event::NodeOutput(node, Output::Success) => {
                    tracing::debug!(
                        tierkreis.node = node.index(),
                        "node signalled completing successfully",
                    );

                    self.node_inputs.remove(&node);

                    let outputs = self
                        .node_outputs_complete(node)
                        .ok_or_else(|| GraphError::NodePendingOutputs(node))?;
                    // if checkpoints are not reported the outputs are dropped
                    if let Some(ch) = &mut self.context.checkpoint_client {
                        // don't report output nodes - they have no outputs and
                        // will be reported by either the completion of their
                        // parent node or the completion of the whole job
                        if node != Graph::boundary()[1] {
                            ch.node_finished(
                                self.context.graph_trace.clone().inner_node(node),
                                outputs,
                            )
                            .await;
                        }
                    }

                    if self.node_inputs.is_empty() {
                        if let Some(ch) = self.context.outer_graph_checkpoint() {
                            tracing::info!(
                                tierkreis.job = ch.job_handle.to_string(),
                                "Job finished."
                            );
                            ch.job_finished(None).await;
                        } else {
                            tracing::info!("Graph finished.");
                        }

                        return Ok(());
                    }
                }

                Event::NodeOutput(node, Output::Failure { error }) => {
                    let error_str = error.to_string();
                    if let Some(ch) = self.context.outer_graph_checkpoint() {
                        tracing::warn!(
                            tierkreis.job = ch.job_handle.to_string(),
                            error = error_str.as_str(),
                            "Job finished with error.",
                        );
                        ch.job_finished(Some(error_str)).await;
                    } else {
                        tracing::warn!(error = error_str.as_str(), "Job finished with error.",);
                    }
                    return Err(GraphError::NodeError(node, Arc::new(error)).into());
                }
            }
        }
    }

    /// Set the value of an edge.
    ///
    /// The value is sent as an input to the target node's running operation.
    ///
    /// - If the node has already finished processing the value is ignored. This could happen, for
    ///   instance, when a branch node has received the value of the branch it selected for and does
    ///   not care for the value on the other branch.
    /// - If by setting the value of this edge the last of the target node's input edges have been
    ///   set, a completion message is sent to the node.
    ///
    /// In the case that the edge points into the graph's output node, the value is set as an
    /// output in the operation's context.
    ///
    /// # Errors
    ///
    /// An error is returned when the edge has already been given a value before.
    fn set_edge_value(&mut self, source: NodePort, value: Value) -> Result<(), GraphError> {
        let edge: &Edge =
            self.graph
                .node_output(source)
                .ok_or(if source.node == Graph::boundary()[0] {
                    GraphError::UnknownNodeOutputPort(source)
                } else {
                    GraphError::UnknownGraphInputPort(source.port)
                })?;
        if self
            .processed_edges
            .insert((edge.source, edge.target), Some(value.clone()))
            .is_some()
        {
            return Err(GraphError::EdgeSetTwice(edge.source, edge.target));
        }

        let source_node = self
            .graph
            .node(edge.source.node)
            .ok_or(GraphError::UnknownNode(edge.source.node))?;

        let value = if self
            .context
            .runtime
            .runtime_type_checking
            .should_type_check(source_node)
        {
            // All edges should have types placed onto them by type inference before the graph is run.
            let edge_type = edge.edge_type.as_ref().unwrap().clone();
            match value_as_type(
                &value,
                edge_type,
                &self
                    .context
                    .runtime
                    .signature
                    .as_ref()
                    .clone()
                    .type_schemes(),
            ) {
                Ok((_, typed_value)) => typed_value,
                Err(type_errors) => {
                    return Err(GraphError::UnexpectedOutputType(
                        edge.source.node,
                        type_errors,
                    ))
                }
            }
        } else {
            value
        };

        if let Some(sender) = self.node_inputs.get(&edge.target.node) {
            let _ = sender.send(Input::Input {
                port: edge.target.port,
                value,
            });
        }

        Ok(())
    }

    async fn check_target_complete(&mut self, source: NodePort) {
        let target = self.graph.node_output(source).unwrap().target.node;
        self.check_inputs_complete(target).await;
    }

    async fn check_inputs_complete(&mut self, node: NodeIndex) {
        // if all input edges are set, node inputs are complete
        let input_complete = self.graph.node_inputs(node).all(|edge| {
            self.processed_edges
                .contains_key(&(edge.source, edge.target))
        });
        if !input_complete {
            return;
        }

        let node_trace = self.context.graph_trace.clone().inner_node(node);
        // notify the node that all inputs are complete
        if let Some(sender) = self.node_inputs.get(&node) {
            tracing::span!(
                Level::INFO,
                "Start node",
                _node_trace = node_trace.to_string()
            );
            let _ = sender.send(Input::Complete);
        }

        // node inputs are complete, so we can report the node as started
        if let Some(ch) = &mut self.context.checkpoint_client {
            // Don't report Output nodes starting, as we don't report them finishing
            if node != Graph::boundary()[1] {
                let retry = self.node_retry_secs.get(&node).copied();
                ch.node_started(node_trace, retry).await;
            }
        }
    }

    /// Check if all the output edges for a node have been set, remove and
    /// return their values.
    fn node_outputs_complete(&mut self, node: NodeIndex) -> Option<HashMap<Label, Value>> {
        let all_keys: Vec<_> = self
            .graph
            .node_outputs(node)
            .map(|edge| (edge.source, edge.target))
            .collect();
        if all_keys
            .iter()
            .all(|key| self.processed_edges.get(key).is_some_and(|v| v.is_some()))
        {
            // all edges have values set, so we can safely take them all.
            all_keys
                .into_iter()
                .map(|(source, target)| {
                    let value = self
                        .processed_edges
                        .get_mut(&(source, target))?
                        .take()
                        .expect("Have already checked value exists.");
                    Some((source.port, value))
                })
                .collect()
        } else {
            None
        }
    }
}

#[derive(Debug, Clone, Error)]
enum GraphError {
    #[error("received input on unknown port: {0}")]
    UnknownGraphInputPort(Label),
    #[error("received output on unknown node port: {0}")]
    UnknownNodeOutputPort(NodePort),
    #[error("received output from unknown node: {0:?}")]
    UnknownNode(NodeIndex),
    #[error("value was set twice for edge from {0} to {1}")]
    EdgeSetTwice(NodePort, NodePort),
    #[error("error while running node: {0:?}")]
    NodeError(NodeIndex, #[source] Arc<anyhow::Error>),
    #[error("Node {0:?} produced value not of expected type {1}")]
    UnexpectedOutputType(NodeIndex, #[source] TypeErrors),
    #[error("unknown function {1} for node {0:?}")]
    UnknownFunction(NodeIndex, FunctionName),
    #[error("node signalled completion with pending outputs: {0:?}")]
    NodePendingOutputs(NodeIndex),
}
