use std::collections::HashMap;

use super::{Input, OperationContext, OperationInputs};
use tierkreis_core::{
    graph::{GraphBuilder, Value},
    symbol::Label,
};
use tokio_stream::StreamExt;
use tracing::instrument;

enum Event {
    Input(Input),
    Closed,
}

#[instrument(name = "match operation", skip(context, inputs), level = "debug")]
pub async fn run_match(
    context: OperationContext,
    mut inputs: OperationInputs,
) -> anyhow::Result<()> {
    let mut thunks = HashMap::new();
    let mut variant = None;

    loop {
        let event = tokio::select! { biased;
            msg = inputs.next() => {
                match msg {
                    Some(input) => Event::Input(input),
                    None => Event::Closed,
                }
            }
        };

        match event {
            Event::Input(Input::Input { port, value }) if port == Label::variant_value() => {
                let (tag, value) = match value {
                    Value::Variant(tag, value) => (tag, *value),
                    _ => anyhow::bail!("match must receive variant value"),
                };

                variant = Some((tag, value));
            }
            Event::Input(Input::Input { port, value }) => {
                let thunk = match value {
                    Value::Graph(graph) => graph,
                    _ => anyhow::bail!(
                        "match must receive graphs in ports except {}",
                        Label::variant_value()
                    ),
                };

                thunks.insert(port, thunk);
            }
            Event::Input(Input::Complete) => {}
            Event::Closed => {
                return Ok(());
            }
        }

        if let Some((tag, _)) = &variant {
            if let Some(thunk) = thunks.remove(tag) {
                let (_, value) = variant.take().unwrap();

                let closure = {
                    // We'll put "thunk" into a Box inside this graph. Keep the inputs/outputs.
                    // It should be possible to read these from inside the Box, but the API is tricky.
                    // Alternatively, we could deepcopy the Graph, but that seems likely expensive.
                    let [i, o] = tierkreis_core::graph::Graph::boundary();
                    let inputs: Vec<_> = thunk.node_outputs(i).map(|e| e.source.port).collect();
                    let outputs: Vec<_> = thunk.node_inputs(o).map(|e| e.target.port).collect();

                    let mut builder = GraphBuilder::new();
                    let param = builder.add_node(value)?;
                    let body = builder.add_node(thunk)?;
                    for port in inputs {
                        let in_node = if port == Label::value() { param } else { i };
                        builder.add_edge((in_node, port), (body, port), None)?;
                    }
                    for port in outputs {
                        builder.add_edge((body, port), (o, port), None)?;
                    }
                    builder.build()?
                };

                context.set_output(Label::thunk(), Value::Graph(closure));
                return Ok(());
            }
        }
    }
}

#[instrument(
    name = "make variant operation",
    skip(context, inputs),
    level = "debug"
)]
pub async fn run_tag(
    tag: Label,
    context: OperationContext,
    mut inputs: OperationInputs,
) -> anyhow::Result<()> {
    let mut input = None;
    loop {
        tokio::select! {
            msg = inputs.next() => {
                match msg {
                    Some(Input::Input {port:_, value}) => {
                        if input.replace(value).is_some() {
                            anyhow::bail!("Received input value twice");
                        }
                    }
                    Some(Input::Complete) => match input.take() {
                        Some(v) => {
                            context.set_output(Label::value(), Value::Variant(tag, Box::new(v)));
                            return Ok(());
                        }
                        None => {
                            anyhow::bail!("Input completion signalled twice");
                        }
                    }
                    None => {
                        return Ok(());
                    }
                };
            }
        };
    }
}
