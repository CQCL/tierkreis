use super::{OperationContext, OperationInputs, Output};
use crate::RuntimeOperation;
use anyhow::anyhow;
use futures::StreamExt;
use tierkreis_core::{graph::Graph, symbol::Location};
use tracing::instrument;

#[instrument(name = "box operation", skip(graph, context, inputs), level = "debug")]
pub(crate) async fn run_box(
    loc: Location,
    graph: Graph,
    context: OperationContext,
    inputs: OperationInputs,
) -> anyhow::Result<()> {
    let operation = match loc.clone().pop() {
        None => RuntimeOperation::new_graph(graph),
        Some(ln) => context
            .runtime
            .run_graph_remote(graph, ln)
            .ok_or_else(|| anyhow!("Could not find location {} to run box", loc))?,
    };

    let mut outputs = operation.run(
        context.runtime.clone(),
        context.callback.clone(),
        context.escape.clone(),
        inputs,
        // The stack-trace already includes this Box node, and the `operation``
        // is a graph operation so will add node_ids of its children itself.
        context.graph_trace.clone(),
        context.checkpoint_client.clone(),
    );

    while let Some(output) = outputs.next().await {
        match output {
            Output::Output { port, value } => {
                context.set_output(port, value);
            }
            Output::Success => break,
            Output::Failure { error } => {
                let error = error.context("failed to run graph in box node");
                return Err(error);
            }
        }
    }

    Ok(())
}
