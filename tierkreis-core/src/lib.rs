//! Core Tierkreis data structures for [Graph], [Value], [Type], [symbol]s,
//! [Namespace], and [FunctionDeclaration] with instances thereof for [builtins].
//!
//! [Type]: graph::Type
//! [Graph]: graph::Graph
//! [Value]: graph::Value
//! [FunctionDeclaration]: namespace::FunctionDeclaration
//! [Namespace]: namespace::Namespace
pub mod builtins;
pub mod graph;
pub mod namespace;
#[allow(missing_docs, clippy::all)]
pub mod portgraph;
pub mod prelude;
pub mod symbol;
pub mod type_checker;

#[cfg(test)]
mod tests {
    use std::error::Error;

    use super::graph::Type;
    use crate::graph::{Graph, GraphBuilder, NodeIndex};
    use rstest::rstest;

    /*
    Construct graph
                input
                /    \
          middle_1   middle_2
                \     /
                 output
    */
    #[rstest]
    fn test_creation() -> Result<(), Box<dyn Error>> {
        let [i, o] = Graph::boundary();
        let middle_1;
        let middle_2;
        let exit;
        let graph = {
            let mut builder = GraphBuilder::new();

            let enter = builder.add_node("split")?;
            exit = builder.add_node("merge")?;
            middle_1 = builder.add_node("id")?;
            middle_2 = builder.add_node("id")?;
            builder.add_edge((i, "enter"), (enter, "in"), None)?;
            builder.add_edge((enter, "first"), (middle_1, "in"), None)?;
            builder.add_edge((enter, "second"), (middle_2, "in"), None)?;
            builder.add_edge((middle_1, "out"), (exit, "first"), Type::Int)?;
            builder.add_edge((middle_2, "out"), (exit, "second"), None)?;
            builder.add_edge((exit, "out"), (o, "exit"), None)?;
            builder.build()?
        };

        assert_eq!(graph.node_inputs(i).count(), 0);
        assert_eq!(graph.node_outputs(i).count(), 1);
        assert_eq!(graph.node_inputs(o).count(), 1);
        assert_eq!(graph.node_outputs(o).count(), 0);

        assert_eq!(graph.nodes().count(), 6);
        assert_eq!(graph.edges().count(), 6);

        assert_eq!(
            graph.node_output((middle_1, "out")),
            graph.node_input((exit, "first"))
        );

        assert_eq!(graph.node(NodeIndex::end()), None);
        assert_eq!(graph.node_inputs(NodeIndex::end()).count(), 0);
        assert_eq!(graph.node_outputs(NodeIndex::end()).count(), 0);
        assert_eq!(graph.node_input((NodeIndex::end(), "port")), None);
        assert_eq!(graph.node_output((NodeIndex::end(), "port")), None);

        Ok(())
    }
}
