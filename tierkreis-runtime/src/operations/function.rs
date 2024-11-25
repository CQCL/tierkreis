use super::{Input, OperationContext, OperationInputs};
use futures::{future::OptionFuture, Future, StreamExt};
use std::collections::HashMap;
use tierkreis_core::{graph::Value, symbol::Label};
use tracing::instrument;

enum Event {
    Input(Input),
    Closed,
    Done(anyhow::Result<PortValueMap>),
}

#[instrument(
    name = "function operation",
    skip(function, context, inputs),
    level = "debug"
)]
pub(crate) async fn run_fn<F, FF>(
    function: F,
    context: OperationContext,
    mut inputs: OperationInputs,
) -> anyhow::Result<()>
where
    F: FnOnce(PortValueMap, OperationContext) -> FF + Send + 'static,
    FF: Future<Output = anyhow::Result<PortValueMap>> + Unpin + Send + 'static,
{
    let mut function = Some(function);
    let mut handle: Option<FF> = None;
    let mut collected_inputs = HashMap::new();

    loop {
        let event = tokio::select! { biased;
            msg = inputs.next() => {
                match msg {
                    Some(input) => Event::Input(input),
                    None => Event::Closed,
                }
            }
            Some(msg) = OptionFuture::from(handle.as_mut()) => {
                match msg {
                    Ok(outputs) => Event::Done(Ok(outputs)),
                    Err(error) => Event::Done(Err(error)),
                }
            }
        };

        match event {
            Event::Input(Input::Input { port, value }) => {
                collected_inputs.insert(port, value);
            }
            Event::Input(Input::Complete) => {
                let function = match function.take() {
                    Some(function) => function,
                    None => anyhow::bail!("input completion signalled twice"),
                };

                handle = Some(function(
                    std::mem::take(&mut collected_inputs),
                    context.clone(),
                ));
            }
            Event::Closed => {
                return Ok(());
            }
            Event::Done(Ok(outputs)) => {
                for (port, value) in outputs {
                    context.set_output(port, value);
                }
                return Ok(());
            }
            Event::Done(Err(error)) => {
                return Err(error);
            }
        }
    }
}

pub type PortValueMap = HashMap<Label, Value>;
