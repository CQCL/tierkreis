//! Protobuf-generated code; Rust equivalents (with non-optional fields) for non-[core]
//! classes e.g. relating to runtimes; and Rust<->proto conversions
use http::uri::InvalidUri;
use thiserror::Error;
use tierkreis_core::{graph::GraphBuilderError, symbol::SymbolError};

pub mod graph;
pub mod messages;
pub mod protos_gen;
pub mod signature;
mod worker;

/// An error parsing input received over GRPC
#[derive(Debug, Error)]
pub enum ConvertError {
    /// Could not parse binary data into valid protobuf
    #[error("failed to parse protobuf")]
    ProtoError,
    /// The [Graph](protos_gen::v1alpha1::graph::Graph) protobuf did not define
    /// a valid Tierkreis [Graph](tierkreis_core::graph::Graph)
    #[error("malformed graph in protobuf: {0}")]
    GraphError(GraphBuilderError),
    /// A function-name, location or other symbol was not a proper qualified name
    #[error("invalid symbol in protobuf: {0}")]
    SymbolError(SymbolError),
    /// The Graph input to [RunGraph] failed type-checking
    ///
    /// [RunGraph]: protos_gen::v1alpha1::runtime::runtime_server::Runtime::run_graph
    #[error("unexpected type errors")]
    UnexpectedTypeErrors,
    /// A [Callback::uri] was not a valid URI
    ///
    /// [Callback::uri]: messages::Callback::uri
    #[error("invalid uri: {0}")]
    InvalidUri(#[from] InvalidUri),
    /// Used where a metadata string that should encode a
    /// [GraphTrace](messages::GraphTrace) is not valid.
    #[error("nodeid invalid")]
    InvalidNodeId,
}

impl From<GraphBuilderError> for ConvertError {
    fn from(error: GraphBuilderError) -> Self {
        ConvertError::GraphError(error)
    }
}

impl From<SymbolError> for ConvertError {
    fn from(error: SymbolError) -> Self {
        ConvertError::SymbolError(error)
    }
}

#[cfg(test)]
mod tests {
    use crate::protos_gen::v1alpha1::graph::*;
    use rstest::{fixture, rstest};
    use std::error::Error;
    use tierkreis_core::graph::{self as core, GraphBuilder};
    use tierkreis_core::prelude::{TryFrom, TryInto};
    use tierkreis_core::symbol as cs;

    #[fixture]
    fn wee_graph() -> anyhow::Result<core::Graph> {
        // Make a graph that adds 1 to its input

        let mut builder = GraphBuilder::new();
        let [input, output] = core::Graph::boundary();

        builder.set_name("wee_graph".into());
        builder.set_io_order([
            vec![TryInto::try_into("value")?],
            vec![TryInto::try_into("value")?],
        ]);
        let add = builder.add_node("add")?;
        let one = builder.add_node(core::Value::Int(1))?;

        builder.add_edge((input, "value"), (add, "a"), core::Type::Int)?;
        builder.add_edge((one, "value"), (add, "b"), core::Type::Int)?;
        builder.add_edge((add, "out"), (output, "value"), core::Type::Int)?;

        Ok(builder.build()?)
    }

    #[rstest]
    fn graph_roundtrip_to_file(
        wee_graph: anyhow::Result<core::Graph>,
    ) -> Result<(), Box<dyn Error>> {
        extern crate prost;

        use prost::Message;

        use prost::bytes::BytesMut;
        use std::fs::File;
        use std::io::{Read, Write};

        let core_graph = wee_graph?;

        // Convert to a serialisable version
        let g = Graph::from(core_graph.clone());

        let capacity = g.encoded_len();
        let mut buffer = Vec::with_capacity(capacity);
        g.encode(&mut buffer)?;

        let mut file = File::create("test0.tk")?;
        file.write_all(&buffer)?;
        file.flush()?;
        let mut file2 = File::open("test0.tk")?;
        // let mut new_buff = BytesMut::with_capacity(capacity);
        let mut new_buff = Vec::new();
        file2.read_to_end(&mut new_buff)?;
        // file2.flush()?;
        let mut new_buff = BytesMut::from(&new_buff[..]);
        let g_new = Graph::decode(&mut new_buff)?;

        let new_core_g: core::Graph = TryInto::try_into(g_new).unwrap();

        assert_eq!(new_core_g, core_graph);

        std::fs::remove_file("test0.tk")?;
        Ok(())
    }

    #[rstest]
    #[case(core::Value::Int(1))]
    #[case(core::Value::Bool(false))]
    #[case(core::Value::Str("test123".to_string()))]
    #[case(core::Value::Pair(Box::new((core::Value::Bool(true), core::Value::Int(3)))))]
    #[case(core::Value::Map(
        [
            (core::Value::Int(1), core::Value::Bool(true)),
            (core::Value::Int(2), core::Value::Bool(false)),
        ]
        .iter()
        .cloned()
        .collect(),
    ))]
    #[case(core::Value::Vec(vec![core::Value::Int(1), core::Value::Int(2), core::Value::Int(3)]))]
    #[case(core::Value::Variant(TryInto::try_into("mytag").unwrap(), Box::new(core::Value::Int(2))))]
    fn value_roundtrip(#[case] start: core::Value) {
        let start_converted: Value = start.clone().into();
        let reverse_converted =
            <core::Value as TryFrom<_>>::try_from(start_converted).expect("Conversion Failed");
        assert_eq!(start, reverse_converted);
    }

    #[rstest]
    #[case(core::Node::Box(cs::Location::local(), wee_graph()?))]
    #[case(cs::FunctionName::builtin(TryInto::try_into("foo")?).into())]
    #[case((cs::FunctionName { prefixes: vec![TryInto::try_into("remote")?], name: TryInto::try_into("foo")? }, 3).into())]
    fn node_roundtrip(#[case] start: core::Node) -> Result<(), Box<dyn Error>> {
        let pb_node: Node = start.clone().into();
        let roundtripped: core::Node = TryInto::try_into(pb_node).expect("Deserialization failed");
        assert_eq!(start, roundtripped);
        Ok(())
    }
}
