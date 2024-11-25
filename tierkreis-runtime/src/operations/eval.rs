use crate::operations::RuntimeOperation;

use super::{Input, OperationContext, OperationInputs, OperationOutputs, Output};
use futures::{future::OptionFuture, StreamExt};
use tierkreis_core::{graph::Value, symbol::Label};

use tokio::sync::mpsc;
use tokio_stream::wrappers::UnboundedReceiverStream;
use tracing::instrument;

enum Event {
    Input(Input),
    Closed,
    ThunkOutput(Output),
    ThunkClosed,
}

#[instrument(name = "eval operation", skip(context, inputs), level = "debug")]
pub async fn run_eval(
    context: OperationContext,
    mut inputs: OperationInputs,
) -> anyhow::Result<()> {
    let mut thunk_outputs: Option<OperationOutputs> = None;
    let (thunk_inputs_tx, thunk_inputs_rx) = mpsc::unbounded_channel();
    let mut thunk_inputs: Option<_> = Some(UnboundedReceiverStream::new(thunk_inputs_rx));
    // Clone the stack trace here (once only), we need it only when we receive the thunk
    let mut stack_trace = Some(context.graph_trace.clone());
    loop {
        let event = tokio::select! { biased;
            msg = inputs.next() => {
                match msg {
                    Some(input) => Event::Input(input),
                    None => Event::Closed,
                }
            }
            Some(msg) = OptionFuture::from(thunk_outputs.as_mut().map(|s| s.next())) => {
                match msg {
                    Some(output) => Event::ThunkOutput(output),
                    None => Event::ThunkClosed,
                }
            }
        };

        match event {
            Event::Input(Input::Input { port, value }) if port == Label::thunk() => {
                let thunk_inputs = match thunk_inputs.take() {
                    Some(thunk_inputs) => thunk_inputs,
                    None => anyhow::bail!("already received thunk"),
                };

                let thunk = match value {
                    Value::Graph(thunk) => thunk,
                    _ => anyhow::bail!("thunk must be a graph"),
                };

                thunk_outputs = Some(RuntimeOperation::new_graph(thunk).run(
                    context.runtime.clone(),
                    context.callback.clone(),
                    context.escape.clone(),
                    thunk_inputs,
                    stack_trace.take().unwrap(),
                    context.checkpoint_client.clone(),
                ));
            }
            Event::Input(input) => {
                let _ = thunk_inputs_tx.send(input);
            }
            Event::Closed => {
                return Ok(());
            }
            Event::ThunkOutput(Output::Output { port, value }) => {
                context.set_output(port, value);
            }
            Event::ThunkOutput(Output::Failure { error }) => {
                let error = error.context("failed to run graph in thunk of eval node");
                return Err(error);
            }
            Event::ThunkOutput(Output::Success) => {
                return Ok(());
            }
            Event::ThunkClosed => {
                anyhow::bail!("thunk stopped unexpectedly");
            }
        }
    }
}
