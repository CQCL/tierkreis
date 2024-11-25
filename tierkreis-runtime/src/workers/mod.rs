//! Workers manage connections to external processes that may run functions
//! and/or (in the case of Tierkreis servers) graphs.
//!
//! A server is itself a *client* of its "children" (themselves servers),
//! thus giving rise to terminology descendants, ancestors, etc. [Location]s
//! identify nodes in this tree and we use the two interchangeably.  Note that
//! the link between a server and its "parent" is transitory, i.e. "parent" (and
//! equivalently "client") is meaningful only for the duration of a request.
use std::collections::HashMap;

use crate::operations::RuntimeOperation;
use crate::RunGraphError;
use tierkreis_core::graph::{Graph, Value};
use tierkreis_core::symbol::{FunctionName, Label, Location};
use tierkreis_proto::messages::Callback;
use tierkreis_proto::protos_gen::v1alpha1::signature as ps;

mod external;
mod local;

pub use external::{
    AuthInjector, CallbackForwarder, ClientInterceptor, EscapeHatch, ExternalWorker,
    FunctionForwarder,
};
pub use local::LocalWorker;
use tonic::async_trait;

/// All workers must be able to provide their signature
#[async_trait]
pub trait Worker: FunctionWorker + Send + Sync {
    /// Returns the signature of the worker.
    async fn signature(&self, location: Location) -> anyhow::Result<ps::ListFunctionsResponse>;

    /// Return a runtime worker, if it is one
    fn to_runtime_worker(&self) -> Option<&dyn RuntimeWorker>;
}

/// FunctionWorkers can run functions.
pub trait FunctionWorker: Send + Sync {
    /// Returns a [`RuntimeOperation`] that runs the named function;
    /// the operation will return an error if the function is unknown.
    fn spawn(&self, function: &FunctionName, loc: &Location) -> RuntimeOperation;
}

/// RuntimeWorkers are able to run graphs
#[async_trait]
pub trait RuntimeWorker: Send + Sync {
    /// Executes a (sub)graph, i.e. as a single step, given a complete map of input values,
    /// and producing a map of output values.
    /// `location` is the location *inside* the target of this request, i.e. relative path.
    /// `escape` allows the subgraph to request operations defined only in an ancestor location.
    async fn execute_graph(
        &self,
        graph: Graph,
        inputs: HashMap<Label, Value>,
        location: Location,
        type_check: bool,
        escape: Option<Callback>,
    ) -> Result<HashMap<Label, Value>, RunGraphError>;

    /// Returns a [`RuntimeOperation`] for running a graph on a specified location.
    fn spawn_graph(&self, graph: Graph, location: &Location) -> RuntimeOperation;

    /// Infer a type on a worker
    async fn infer_type(
        &self,
        to_check: Value,
        location: Location,
    ) -> anyhow::Result<ps::InferTypeResponse>;
}
