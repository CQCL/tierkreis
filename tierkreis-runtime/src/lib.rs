//! tierkreis-runtime implements a tokio-based runtime system for Tierkreis graphs
//! (i.e., an asynchronous + parallel interpreter).
use anyhow::anyhow;
use operations::graph::checkpoint_client::CheckpointClient;

use operations::{RuntimeOperation, TaskHandle};
use std::collections::{HashMap, HashSet};
use std::sync::Arc;
use thiserror::Error;
use tierkreis_core::{
    graph::TypeScheme,
    namespace::{FunctionDeclaration, NamespaceItem, Signature, SignatureError},
    symbol::{Label, Location, LocationName},
    type_checker::{GraphWithInputs, TypeErrors, Typeable},
};
use tierkreis_core::{
    graph::{Graph, Node, Value},
    prelude::TryInto,
    symbol::FunctionName,
};
use tierkreis_proto::messages::{Callback, GraphTrace, InferTypeResponse};
use tierkreis_proto::protos_gen::v1alpha1::signature as ps;
use workers::{EscapeHatch, LocalWorker, Worker};

#[cfg(feature = "config")]
use serde::Deserialize;

pub mod operations;
pub(crate) mod util;
pub mod workers;

/// Builder for [`Runtime`].
pub struct RuntimeBuilder {
    workers: HashMap<LocationName, Box<dyn Worker>>,
    local_functions: LocalWorker,
    signature: Signature,
    runtime_type_checking: RuntimeTypeChecking,
}

#[derive(Error, Debug)]
#[error("Location {0} was defined twice")]
struct LocationConflict(LocationName);

impl RuntimeBuilder {
    /// Creates a new RuntimeBuilder with a blank initial configuration:
    /// no workers, only the builtin functions, and [RuntimeTypeChecking::OnlyExternal]
    pub fn new() -> Self {
        let mut res = RuntimeBuilder {
            workers: HashMap::new(),
            local_functions: LocalWorker::new(),
            signature: Signature::default(),
            runtime_type_checking: RuntimeTypeChecking::OnlyExternal,
        }
        .with_local_functions(LocalWorker::builtins())
        .unwrap();
        res.signature.scopes.insert(Location::local());
        res
    }

    /// Add a worker at a specified child location, which must be new in the config.
    pub async fn with_worker<W>(mut self, worker: W, loc: LocationName) -> anyhow::Result<Self>
    where
        W: Worker + 'static,
    {
        if self.workers.contains_key(&loc) {
            return Err(LocationConflict(loc).into());
        }

        let sig: Signature = TryInto::try_into(worker.signature(Location::local()).await?)?;

        self.signature.merge_signature(sig.in_location(loc))?;

        self.workers.insert(loc, Box::new(worker));
        Ok(self)
    }

    /// Add new [LocalWorker] functions at [Location::local].
    ///
    /// # Errors
    ///
    /// `SignatureError` if any of the new functions have signatures that conflict
    /// with already-added functions of the same name.
    pub fn with_local_functions(
        mut self,
        local_functions: LocalWorker,
    ) -> Result<Self, SignatureError> {
        self.signature.merge_signature(Signature {
            root: local_functions.declarations().map(|x| NamespaceItem {
                decl: x,
                locations: vec![Location::local()],
            }),
            aliases: HashMap::new(),
            scopes: HashSet::new(),
        })?;
        self.local_functions.merge(local_functions)?;
        Ok(self)
    }

    /// Changes what level of runtime type-checking the [Runtime] will perform
    /// (overwrites previous setting)
    pub fn with_checking(mut self, runtime_type_checking: RuntimeTypeChecking) -> Self {
        self.runtime_type_checking = runtime_type_checking;
        self
    }

    /// Constructs a Runtime using the configuration set in this RuntimeBuilder
    pub fn start(self) -> Runtime {
        Runtime {
            workers: Arc::new(self.workers),
            local_functions: Arc::new(self.local_functions),
            signature: Arc::new(self.signature),
            runtime_type_checking: self.runtime_type_checking,
        }
    }
}

impl Default for RuntimeBuilder {
    fn default() -> Self {
        Self::new()
    }
}

/// Levels of type checking that can be performed by a [Runtime]
/// during graph execution. (Distinct from the `type_check: bool` parameter
/// to e.g. [start_graph](crate::Runtime::start_graph) which relates to
/// type-checking *before* graph execution begins)
#[derive(Copy, Clone, Debug, Default)]
#[cfg_attr(feature = "config", derive(Deserialize))]
#[cfg_attr(feature = "config", serde(rename_all = "snake_case"))]
pub enum RuntimeTypeChecking {
    /// No type checking at runtime. If functions produce outputs that do not
    /// match their [outputs](FunctionDeclaration), these values will nonetheless
    /// be placed onto the graph edges and passed as inputs to the edge targets.
    Disabled,
    /// Values from external workers (either running functions, or graph workers
    /// running Boxes at non-local/strict-descendant [Location]s) are checked as
    /// [Self::Enabled]; values from local functions and boxes are not checked
    /// (as [Self::Disabled]).
    #[default]
    OnlyExternal,
    /// Type-check that every value produced at runtime meets the expected/declared
    /// type; any that does not will abort execution with a
    /// `GraphError::UnexpectedOutputType` error
    // Note that error is private (it gets anyhow!'d), hence can't link to it
    Enabled,
}

impl RuntimeTypeChecking {
    fn should_type_check(&self, source_node: &Node) -> bool {
        match self {
            RuntimeTypeChecking::Disabled => false,
            RuntimeTypeChecking::OnlyExternal => source_node.is_external(),
            RuntimeTypeChecking::Enabled => true,
        }
    }
}

/// Runtime system that manages all resources necessary to run graphs.
///
/// The runtime system manages a collection of [`Worker`]s and routes requests to run nodes to the
/// appropriate workers depending on which functions they support.
///
/// This struct can be efficiently cloned to be passed around and cleans up its
/// resources after the last copy has been dropped.
#[derive(Clone)]
pub struct Runtime {
    workers: Arc<HashMap<LocationName, Box<dyn Worker>>>,
    local_functions: Arc<LocalWorker>,
    signature: Arc<Signature>,
    runtime_type_checking: RuntimeTypeChecking,
}

impl std::fmt::Debug for Runtime {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("Runtime").finish()
    }
}

impl Runtime {
    /// Create a new `RuntimeBuilder`.
    #[must_use]
    pub fn builder() -> RuntimeBuilder {
        RuntimeBuilder::new()
    }

    /// Returns the signatures of all functions available to the runtime.
    pub fn function_declarations(&self) -> impl Iterator<Item = &FunctionDeclaration> {
        self.signature.root.values().map(|entry| &entry.decl)
    }

    /// Returns the signature for a function.
    #[must_use]
    pub fn function_declaration(&self, name: FunctionName) -> Option<&FunctionDeclaration> {
        self.signature.root.get(&name).map(|entry| &entry.decl)
    }

    /// Lists all the functions known to this runtime; equivalent to [Self::signature_in_loc]
    /// with [Location::local]
    pub fn signature(&self) -> Signature {
        self.signature.as_ref().clone()
    }

    /// Lists the functions known in a specified location (and sub-locations thereof).
    pub async fn signature_in_loc(
        &self,
        loc: Location,
    ) -> anyhow::Result<ps::ListFunctionsResponse> {
        match loc.pop() {
            Some((ln, rest)) => match self.workers.get(&ln) {
                Some(x) => Ok(x.signature(rest).await?),
                None => Err(anyhow!("Location {} not found", ln)),
            },
            None => Ok(self.signature().into()),
        }
    }

    /// Infer the type of a graph or value using the signature provided by the runtime's workers.
    ///
    /// # Errors
    ///
    /// Returns an error in case the type inference fails.
    pub fn infer_type<T>(&self, to_check: &T) -> Result<(TypeScheme, T::Annotated), TypeErrors>
    where
        T: Typeable,
    {
        to_check.infer_type(&self.signature().type_schemes())
    }

    /// Infers the type that a [Value] would have if it were seen in a
    /// particular location, i.e. a descendant [RuntimeWorker] (able to
    /// run Graphs).
    ///
    /// # Errors
    /// * If `location` does not identify a worker able to type-check graphs
    /// * Any type error in `to_check`, for example, using functions not
    ///   available at `location`.
    ///
    /// [RuntimeWorker]: workers::RuntimeWorker
    pub async fn infer_type_in_loc(
        &self,
        to_check: Value,
        location: Location,
    ) -> anyhow::Result<ps::InferTypeResponse> {
        match location.pop() {
            Some((ln, rest)) => {
                self.workers
                    .get(&ln)
                    .ok_or_else(|| anyhow!("Location {} not found", ln))?
                    .to_runtime_worker()
                    .ok_or_else(|| anyhow!("Location {} is not a runtime worker", ln))?
                    .infer_type(to_check, rest)
                    .await
            }
            None => {
                let resp: InferTypeResponse = self.infer_type(&to_check).into();
                Ok(resp.into())
            }
        }
    }

    /// Run a graph to completion with a given collection of inputs,
    /// at a non-local Location.
    pub async fn execute_graph_remote(
        &self,
        graph: Graph,
        inputs: HashMap<Label, Value>,
        type_check: bool,
        remote_loc: (LocationName, Location),
        escape: Callback, // back to this server, at least
    ) -> Result<HashMap<Label, Value>, RunGraphError> {
        let (ln, rest) = remote_loc;
        match self
            .workers
            .get(&ln)
            .ok_or_else(|| {
                RunGraphError::RuntimeError(Arc::new(anyhow!("Location {} not found", ln)))
            })?
            .to_runtime_worker()
        {
            Some(x) => {
                x.execute_graph(graph, inputs, rest, type_check, Some(escape))
                    .await
            }
            None => Err(RunGraphError::RuntimeError(Arc::new(anyhow!(
                "Location {} is not a runtime worker",
                ln
            )))),
        }
    }

    /// Run a graph to completion with a given collection of inputs, locally,
    /// optionally after type-checking.
    ///
    /// `callback` should be a connection-point (for child workers) to connect to this runtime.
    ///
    /// `escape` may be a forwarding chain to the root of a chain of servers,
    ///    but note that if `type_check` is true, then we will never need to escape
    ///    above this server (as successful type-checking guarantees the graph uses
    ///    only functions known to this server).
    #[allow(clippy::missing_panics_doc)]
    pub async fn execute_graph_cb(
        &self,
        graph: Graph,
        inputs: HashMap<Label, Value>,
        type_check: bool,
        callback: Callback,
        escape: EscapeHatch,
    ) -> Result<HashMap<Label, Value>, RunGraphError> {
        Ok(self
            .start_graph(graph, inputs, type_check, callback, escape, None)?
            .complete()
            .await?
            .as_ref()
            .clone())
    }

    /// Starts running a graph (locally, on this Runtime),
    /// optionally type-checking the graph and inputs first.
    ///
    /// If type-checking succeeds (or is not requested), returns a handle to
    /// the graph-executing process which will continue in the background.
    ///
    /// See [execute_graph_cb](Self::execute_graph_cb) for more detail on `callback` + `escape`
    pub fn start_graph(
        &self,
        graph: Graph,
        inputs: HashMap<Label, Value>,
        type_check: bool,
        callback: Callback,
        escape: EscapeHatch,
        checkpoint_client: Option<CheckpointClient>,
    ) -> Result<TaskHandle, TypeErrors> {
        let (checked_graph, checked_inputs) = if type_check {
            let (_, gwi) = GraphWithInputs { graph, inputs }
                .infer_type(&self.signature.as_ref().clone().type_schemes())?;
            (gwi.graph, gwi.inputs)
        } else {
            (graph, inputs)
        };

        // ALAN: TODO: pass thru run_graph etc...but is this enough if we don't use scoped execution?
        let stack_trace = GraphTrace::Root;

        let handle = RuntimeOperation::new_graph(checked_graph)
            .run_simple(
                self.clone(),
                callback,
                escape,
                checked_inputs,
                stack_trace,
                checkpoint_client,
            )
            .into_task();

        Ok(handle)
    }

    /// Runs a function at a specific location (local or otherwise).
    /// If the location is non-local, will definitely return Some RuntimeOperation
    /// (one that fails when run if the indicated remote can't run the function).
    /// If the location is local, may return None if the function name is not known.
    #[must_use]
    pub fn run_function_with_loc(
        &self,
        function: &FunctionName,
        loc: &Location,
    ) -> Option<RuntimeOperation> {
        let maybe_remote = loc.clone().pop().or_else(|| {
            self.signature
                .root
                .get(function)
                // Choosing the first location here is arbitrary and might be optimised
                .and_then(|entry| entry.locations.first())
                .and_then(|l| l.clone().pop())
        });
        match maybe_remote {
            Some((ln, rest)) => Some(
                // We could check in the signature that the named Location is able
                // to execute the named function, but for (suitably) well-behaved
                // clients  and type-checked graphs, we shouldn't hit such a case.
                // A more definitive verdict requires contacting the worker in question,
                // which we do not have time for until the RuntimeOperation executes,
                // so execution may fail if the function name isn't recognized.
                self.workers.get(&ln)?.spawn(function, &rest),
            ),
            None => self.local_functions.spawn(function),
        }
    }

    /// Runs a graph in a runtime that is a strict descendant of this one.
    /// (A non-local [Location] with at least one [LocationName].)
    #[must_use]
    pub fn run_graph_remote(
        &self,
        graph: Graph,
        loc: (LocationName, Location),
    ) -> Option<RuntimeOperation> {
        let (ln, rest) = loc;
        Some(
            self.workers
                .get(&ln)?
                .to_runtime_worker()?
                .spawn_graph(graph, &rest),
        )
    }
}

/// Errors for [`Runtime::execute_graph_cb`].
#[derive(Debug, Clone, Error)]
pub enum RunGraphError {
    /// The graph did not pass type-checking
    #[error("graph failed to type check")]
    TypeError(
        #[source]
        #[from]
        TypeErrors,
    ),
    /// A miscellaneous error during graph execution
    #[error("error while running a graph")]
    RuntimeError(
        #[source]
        #[from]
        Arc<anyhow::Error>,
    ),
}

impl From<anyhow::Error> for RunGraphError {
    fn from(e: anyhow::Error) -> Self {
        RunGraphError::RuntimeError(Arc::new(e))
    }
}

#[cfg(test)]
pub(crate) mod tests {
    use crate::EscapeHatch;
    use anyhow::bail;
    use rstest::{fixture, rstest};
    use std::{collections::HashMap, time::Duration};
    use tierkreis_core::{
        graph::{Graph, GraphBuilder, GraphBuilderError, GraphType, Node, Type, TypeScheme, Value},
        namespace::FunctionDeclaration,
        prelude::TryInto,
        symbol::{FunctionName, Label, Location, LocationName},
    };
    use tierkreis_proto::messages::{Callback, GraphTrace};

    use crate::{
        operations::{OperationContext, RuntimeOperation},
        workers::{AuthInjector, ClientInterceptor, ExternalWorker, LocalWorker},
        LocationConflict, Runtime,
    };
    pub(super) fn fake_interceptor() -> ClientInterceptor {
        ClientInterceptor::new(AuthInjector::NoAuth)
    }
    pub(super) fn fake_callback() -> Callback {
        Callback {
            uri: "https://localhost:8020".parse().unwrap(),
            loc: Location::local(),
        }
    }
    pub(super) fn fake_escape() -> EscapeHatch {
        EscapeHatch::this_runtime(fake_callback())
    }
    pub(super) fn py_loc() -> LocationName {
        TryInto::try_into("python").unwrap()
    }
    fn python_path() -> String {
        format!(
            "{}/../python/tests/test_worker/main.py",
            env!("CARGO_MANIFEST_DIR")
        )
    }

    #[tokio::test]
    async fn empty_graph() -> anyhow::Result<()> {
        let graph = GraphBuilder::new().build()?;
        let runtime = Runtime::builder().start();
        let outputs = runtime
            .execute_graph_cb(graph, HashMap::new(), true, fake_callback(), fake_escape())
            .await?;
        assert!(outputs.is_empty());
        Ok(())
    }

    #[tokio::test]
    async fn direct_identity() -> anyhow::Result<()> {
        let graph = {
            let mut builder = GraphBuilder::new();
            let [input, output] = Graph::boundary();

            builder.add_edge((input, "value"), (output, "value"), None)?;
            builder.build()?
        };

        let runtime = Runtime::builder().start();
        let mut inputs = HashMap::new();
        inputs.insert(Label::value(), Value::Int(42));
        let outputs = runtime
            .execute_graph_cb(graph, inputs, true, fake_callback(), fake_escape())
            .await?;
        assert_eq!(outputs[&Label::value()], Value::Int(42));
        Ok(())
    }

    #[tokio::test]
    async fn const_node() -> anyhow::Result<()> {
        let graph = {
            let mut builder = GraphBuilder::new();
            let [_, output] = Graph::boundary();

            let constant = builder.add_node(Value::Int(3))?;
            builder.add_edge((constant, "value"), (output, "value"), None)?;
            builder.build()?
        };

        let runtime = Runtime::builder().start();
        let outputs = runtime
            .execute_graph_cb(graph, HashMap::new(), true, fake_callback(), fake_escape())
            .await?;
        assert_eq!(outputs[&Label::value()], Value::Int(3));
        Ok(())
    }

    #[tokio::test]
    async fn boxed_const_node() -> anyhow::Result<()> {
        let subgraph = {
            let mut builder = GraphBuilder::new();
            let [_, output] = Graph::boundary();

            let const_ = builder.add_node(Value::Int(3))?;
            builder.add_edge((const_, "value"), (output, "value"), None)?;
            builder.build()?
        };

        let graph = {
            let mut builder = GraphBuilder::new();
            let [_, output] = Graph::boundary();

            let subgraph = builder.add_node(subgraph)?;
            builder.add_edge((subgraph, "value"), (output, "value"), None)?;
            builder.build()?
        };

        let runtime = Runtime::builder().start();
        let outputs = runtime
            .execute_graph_cb(graph, HashMap::new(), true, fake_callback(), fake_escape())
            .await
            .unwrap();
        assert!(matches!(outputs[&Label::value()], Value::Int(3)));
        Ok(())
    }

    #[tokio::test]
    async fn id_node() -> anyhow::Result<()> {
        let graph = {
            let mut builder = GraphBuilder::new();
            let [input, output] = Graph::boundary();

            let id = builder.add_node("id")?;
            builder.add_edge((input, "id_in"), (id, "value"), None)?;
            builder.add_edge((id, "value"), (output, "id_out"), None)?;
            builder.build()?
        };

        let mut inputs = HashMap::new();
        inputs.insert(TryInto::try_into("id_in")?, Value::Int(3));

        let runtime = Runtime::builder().start();
        let outputs = runtime
            .execute_graph_cb(graph, inputs, true, fake_callback(), fake_escape())
            .await?;

        assert_eq!(outputs[&TryInto::try_into("id_out")?], Value::Int(3));

        Ok(())
    }

    #[tokio::test]
    async fn id_node_pair() -> anyhow::Result<()> {
        let graph = {
            let mut builder = GraphBuilder::new();
            let [input, output] = Graph::boundary();

            let in_ = builder.add_node("id")?;
            let out = builder.add_node("id")?;
            builder.add_edge((input, "in"), (in_, "value"), None)?;
            builder.add_edge((in_, "value"), (out, "value"), None)?;
            builder.add_edge((out, "value"), (output, "out"), None)?;
            builder.build()?
        };

        let mut inputs = HashMap::new();
        inputs.insert(TryInto::try_into("in")?, Value::Int(3));

        let runtime = Runtime::builder().start();
        let outputs = runtime
            .execute_graph_cb(graph, inputs, true, fake_callback(), fake_escape())
            .await?;
        assert_eq!(outputs[&TryInto::try_into("out")?], Value::Int(3));
        Ok(())
    }

    #[tokio::test]
    async fn id_py_node() -> anyhow::Result<()> {
        let graph = {
            let mut builder = GraphBuilder::new();
            let [input, output] = Graph::boundary();

            let id_py = builder.add_node("python_nodes::id_py")?;
            builder.add_edge((input, "id_in"), (id_py, "value"), None)?;
            builder.add_edge((id_py, "value"), (output, "id_out"), None)?;
            builder.build()?
        };

        let python = ExternalWorker::new_spawn(python_path(), fake_interceptor()).await?;
        let runtime = Runtime::builder()
            .with_worker(python, py_loc())
            .await?
            .start();

        let mut inputs = HashMap::new();
        inputs.insert(TryInto::try_into("id_in")?, Value::Int(3));

        let outputs = runtime
            .execute_graph_cb(graph, inputs, true, fake_callback(), fake_escape())
            .await?;
        assert_eq!(outputs[&TryInto::try_into("id_out")?], Value::Int(3));
        Ok(())
    }

    fn add_entry() -> anyhow::Result<FunctionDeclaration> {
        let lhs: Label = TryInto::try_into("lhs")?;
        let rhs: Label = TryInto::try_into("rhs")?;
        let out: Label = TryInto::try_into("out")?;

        let type_scheme = TypeScheme::from({
            let mut t = GraphType::new();
            t.add_input(lhs, Type::Int);
            t.add_input(rhs, Type::Int);
            t.add_output(out, Type::Int);
            t
        });

        Ok(FunctionDeclaration {
            type_scheme,
            description: "Add two numbers".to_string(),
            input_order: vec![lhs, rhs],
            output_order: vec![out],
        })
    }

    async fn add_function(
        mut inputs: HashMap<Label, Value>,
        _context: OperationContext,
    ) -> anyhow::Result<HashMap<Label, Value>> {
        let lhs = match inputs.remove(&TryInto::try_into("lhs")?) {
            Some(Value::Int(lhs)) => lhs,
            _ => anyhow::bail!("Missing or invalid lhs input."),
        };

        let rhs = match inputs.remove(&TryInto::try_into("rhs")?) {
            Some(Value::Int(lhs)) => lhs,
            _ => anyhow::bail!("Missing or invalid rhs input."),
        };

        let mut output = HashMap::new();
        output.insert(TryInto::try_into("out")?, Value::Int(lhs + rhs));
        Ok(output)
    }

    #[tokio::test]
    async fn add() -> anyhow::Result<()> {
        let graph = {
            let mut builder = GraphBuilder::new();
            let [input, output] = Graph::boundary();

            let add = builder.add_node("add")?;
            builder.add_edge((input, "lhs"), (add, "lhs"), None)?;
            builder.add_edge((input, "rhs"), (add, "rhs"), None)?;
            builder.add_edge((add, "out"), (output, "out"), None)?;
            builder.build()?
        };

        let mut inputs = HashMap::new();
        inputs.insert(TryInto::try_into("lhs")?, Value::Int(3));
        inputs.insert(TryInto::try_into("rhs")?, Value::Int(1));

        let mut worker = LocalWorker::new();
        let add = add_entry()?;
        worker.add_function(
            FunctionName::builtin(TryInto::try_into("add")?),
            add,
            || RuntimeOperation::new_fn_async(add_function),
        );

        let runtime = Runtime::builder().with_local_functions(worker)?.start();
        let outputs = runtime
            .execute_graph_cb(graph, inputs, true, fake_callback(), fake_escape())
            .await?;
        assert_eq!(outputs[&TryInto::try_into("out")?], Value::Int(4));
        Ok(())
    }

    #[tokio::test]
    async fn eval_add() -> anyhow::Result<()> {
        let [input, output] = Graph::boundary();
        let add_graph = {
            let mut builder = GraphBuilder::new();

            let add = builder.add_node("add")?;
            let id = builder.add_node("id")?;
            builder.add_edge((input, "id_in"), (id, "value"), None)?;
            builder.add_edge((input, "lhs"), (add, "lhs"), None)?;
            builder.add_edge((input, "rhs"), (add, "rhs"), None)?;
            builder.add_edge((id, "value"), (output, "id_out"), None)?;
            builder.add_edge((add, "out"), (output, "out"), None)?;
            builder.build()?
        };

        let eval_graph = {
            let mut builder = GraphBuilder::new();
            let add_thunk_const = builder.add_node(Value::Graph(add_graph))?;
            let eval_add = builder.add_node("eval")?;
            builder.add_edge((add_thunk_const, "value"), (eval_add, "thunk"), None)?;
            builder.add_edge((input, "x"), (eval_add, "lhs"), None)?;
            builder.add_edge((input, "y"), (eval_add, "rhs"), None)?;
            builder.add_edge((input, "z"), (eval_add, "id_in"), None)?;
            builder.add_edge((eval_add, "out"), (output, "add_out"), None)?;
            builder.add_edge((eval_add, "id_out"), (output, "id_out"), None)?;
            builder.build()?
        };

        let mut inputs = HashMap::new();
        inputs.insert(TryInto::try_into("x")?, Value::Int(5));
        inputs.insert(TryInto::try_into("y")?, Value::Int(7));
        inputs.insert(TryInto::try_into("z")?, Value::Bool(true));

        let mut worker = LocalWorker::new();
        let add = add_entry()?;
        worker.add_function(
            FunctionName::builtin(TryInto::try_into("add")?),
            add,
            || RuntimeOperation::new_fn_async(add_function),
        );

        let runtime = Runtime::builder().with_local_functions(worker)?.start();
        let outputs = runtime
            .execute_graph_cb(eval_graph, inputs, true, fake_callback(), fake_escape())
            .await?;

        assert_eq!(outputs[&TryInto::try_into("add_out")?], Value::Int(12));
        assert_eq!(outputs[&TryInto::try_into("id_out")?], Value::Bool(true));

        Ok(())
    }

    #[tokio::test]
    async fn test_pair() -> anyhow::Result<()> {
        let graph = {
            let mut builder = GraphBuilder::new();
            let [input, output] = Graph::boundary();

            let make_pair = builder.add_node("make_pair")?;
            builder.add_edge((input, "one"), (make_pair, "first"), None)?;
            builder.add_edge((input, "two"), (make_pair, "second"), None)?;
            builder.add_edge((make_pair, "pair"), (output, "out"), None)?;
            builder.build()?
        };

        let mut inputs = HashMap::new();
        inputs.insert(TryInto::try_into("one")?, Value::Int(5));
        inputs.insert(TryInto::try_into("two")?, Value::Bool(true));

        let runtime = Runtime::builder().start();
        let outputs = runtime
            .execute_graph_cb(graph, inputs, true, fake_callback(), fake_escape())
            .await?;

        assert_eq!(
            outputs[&TryInto::try_into("out")?],
            Value::Pair(Box::new((Value::Int(5), Value::Bool(true))))
        );

        Ok(())
    }

    /*
        |   |
      make_pair
          |
        unpair
        |    |
    */
    #[tokio::test]
    async fn test_pair_unpair() -> anyhow::Result<()> {
        let graph = {
            let mut builder = GraphBuilder::new();
            let [input, output] = Graph::boundary();

            let make_pair = builder.add_node("make_pair")?;
            let unpack_pair = builder.add_node("unpack_pair")?;
            builder.add_edge((input, "one"), (make_pair, "first"), None)?;
            builder.add_edge((input, "two"), (make_pair, "second"), None)?;
            builder.add_edge((make_pair, "pair"), (unpack_pair, "pair"), None)?;
            builder.add_edge((unpack_pair, "first"), (output, "one"), None)?;
            builder.add_edge((unpack_pair, "second"), (output, "two"), None)?;
            builder.build()?
        };

        let mut inputs = HashMap::new();
        inputs.insert(TryInto::try_into("one")?, Value::Int(4));
        inputs.insert(TryInto::try_into("two")?, Value::Bool(false));

        let runtime = Runtime::builder().start();
        let outputs = runtime
            .execute_graph_cb(graph, inputs.clone(), true, fake_callback(), fake_escape())
            .await
            .unwrap();

        assert_eq!(inputs, outputs);

        Ok(())
    }

    #[tokio::test]
    async fn test_vec() -> anyhow::Result<()> {
        let graph = {
            let mut builder = GraphBuilder::new();
            let [input, output] = Graph::boundary();

            let make_list = builder.add_node("push")?;
            builder.add_edge((input, "item"), (make_list, "item"), None)?;
            builder.add_edge((input, "vec"), (make_list, "vec"), None)?;
            builder.add_edge((make_list, "vec"), (output, "out"), None)?;
            builder.build()?
        };

        let runtime = Runtime::builder().start();
        let values = vec![Value::Int(1), Value::Int(2), Value::Int(3)];

        let mut inputs = HashMap::new();
        inputs.insert(
            TryInto::try_into("vec")?,
            Value::Vec(vec![values[0].clone(), values[1].clone()]),
        );
        inputs.insert(TryInto::try_into("item")?, values[2].clone());

        let outputs = runtime
            .execute_graph_cb(graph, inputs, true, fake_callback(), fake_escape())
            .await?;

        assert_eq!(outputs[&TryInto::try_into("out")?], Value::Vec(values));
        Ok(())
    }

    /*
        |  |
      push
        |
       pop
       |  |
    */
    #[tokio::test]
    async fn test_pop() -> anyhow::Result<()> {
        let graph = {
            let mut builder = GraphBuilder::new();
            let [input, output] = Graph::boundary();

            let make_list = builder.add_node("push")?;
            let unpack_list = builder.add_node("pop")?;
            builder.add_edge((input, "item"), (make_list, "item"), None)?;
            builder.add_edge((input, "vec"), (make_list, "vec"), None)?;
            builder.add_edge((make_list, "vec"), (unpack_list, "vec"), None)?;
            builder.add_edge((unpack_list, "item"), (output, "item"), None)?;
            builder.add_edge((unpack_list, "vec"), (output, "vec"), None)?;
            builder.build()?
        };

        let mut inputs = HashMap::new();
        inputs.insert(TryInto::try_into("item")?, Value::Int(4));
        inputs.insert(
            TryInto::try_into("vec")?,
            Value::Vec(vec![Value::Int(3), Value::Int(2)]),
        );

        let runtime = Runtime::builder().start();
        let outputs = runtime
            .execute_graph_cb(graph, inputs.clone(), true, fake_callback(), fake_escape())
            .await
            .unwrap();

        assert_eq!(inputs, outputs);
        Ok(())
    }

    /*
        |
       tag
        |
       match
        |
    */
    #[tokio::test]
    async fn test_match() -> anyhow::Result<()> {
        let [input, output] = Graph::boundary();
        // Test a variant < foo: Int | bar: Vec<Int> >
        let foo_graph = {
            let mut builder = GraphBuilder::new();

            let inc = builder.add_node("iadd")?;
            builder.add_edge((input, "value"), (inc, "a"), None)?;
            builder.add_edge((input, "xtra"), (inc, "b"), None)?;
            builder.add_edge((inc, "value"), (output, "value"), None)?;
            builder.build()?
        };
        let bar_graph = {
            let mut builder = GraphBuilder::new();
            let pop = builder.add_node("pop")?;
            let d1 = builder.add_node("discard")?;
            builder.add_edge((input, "value"), (pop, "vec"), None)?;
            builder.add_edge((pop, "vec"), (d1, "value"), None)?;
            builder.add_edge((pop, "item"), (output, "value"), None)?;
            let d2 = builder.add_node("discard")?;
            builder.add_edge((input, "xtra"), (d2, "value"), None)?;
            builder.build()?
        };
        let match_graph = {
            let mut builder = GraphBuilder::new();
            let n = builder.add_node(Node::Match)?;
            let ev = builder.add_node("eval")?;
            let foo_g = builder.add_node(Value::Graph(foo_graph))?;
            let bar_g = builder.add_node(Value::Graph(bar_graph))?;
            builder.add_edge((input, "arg"), (n, Label::variant_value()), None)?;
            builder.add_edge((foo_g, "value"), (n, "foo"), None)?;
            builder.add_edge((bar_g, "value"), (n, "bar"), None)?;
            builder.add_edge((n, "thunk"), (ev, "thunk"), None)?;
            builder.add_edge((ev, "value"), (output, "value"), None)?;
            builder.add_edge((input, "if_foo"), (ev, "xtra"), None)?;
            builder.build()?
        };

        let runtime = Runtime::builder().start();

        // Test with a "foo" (providing variant value directly)
        let arg = Value::Variant(TryInto::try_into("foo")?, Box::new(Value::Int(3)));
        let inputs = HashMap::from([
            (TryInto::try_into("arg")?, arg),
            (TryInto::try_into("if_foo")?, Value::Int(5)),
        ]);
        let outputs = runtime
            .execute_graph_cb(
                match_graph.clone(),
                inputs,
                true,
                fake_callback(),
                fake_escape(),
            )
            .await?;
        assert_eq!(outputs, HashMap::from([(Label::value(), Value::Int(8))]));

        // Test with a "bar" (built via a Tag node)
        let v = Value::Vec(vec![Value::Int(31), Value::Int(42)]);
        let graph2 = {
            let mut builder = GraphBuilder::new();
            let vec = builder.add_node(v)?;
            let mkv = builder.add_node(Node::Tag(TryInto::try_into("bar")?))?;
            builder.add_edge((vec, "value"), (mkv, "value"), None)?;
            let m = builder.add_node(match_graph.clone())?; // Box node
            builder.add_edge((mkv, "value"), (m, "arg"), None)?;
            let c = builder.add_node(Value::Int(101))?;
            builder.add_edge((c, "value"), (m, "if_foo"), None)?;
            builder.add_edge((m, "value"), (output, "result"), None)?;
            builder.build()?
        };
        let outputs = runtime
            .execute_graph_cb(
                graph2,
                HashMap::from([]),
                true,
                fake_callback(),
                fake_escape(),
            )
            .await?;
        assert_eq!(
            outputs,
            HashMap::from([(TryInto::try_into("result")?, Value::Int(42))])
        );

        Ok(())
    }

    #[tokio::test]
    async fn test_switch() -> anyhow::Result<()> {
        let graph = {
            let mut builder = GraphBuilder::new();
            let [input, output] = Graph::boundary();

            let switch = builder.add_node("switch")?;
            builder.add_edge((input, "true"), (switch, "if_true"), None)?;
            builder.add_edge((input, "false"), (switch, "if_false"), None)?;
            builder.add_edge((input, "predicate"), (switch, "pred"), None)?;
            builder.add_edge((switch, "value"), (output, "out"), None)?;
            builder.build()?
        };

        let runtime = Runtime::builder().start();

        // Test 'true' branch
        let mut inputs = HashMap::new();
        inputs.insert(TryInto::try_into("predicate")?, Value::Bool(true));
        inputs.insert(TryInto::try_into("true")?, Value::Int(4));
        inputs.insert(TryInto::try_into("false")?, Value::Int(5));

        let outputs = runtime
            .execute_graph_cb(graph.clone(), inputs, true, fake_callback(), fake_escape())
            .await
            .unwrap();
        assert_eq!(outputs[&TryInto::try_into("out")?], Value::Int(4));

        // Test 'false' branch
        let mut inputs = HashMap::new();
        inputs.insert(TryInto::try_into("predicate")?, Value::Bool(false));
        inputs.insert(TryInto::try_into("true")?, Value::Int(4));
        inputs.insert(TryInto::try_into("false")?, Value::Int(5));

        let outputs = runtime
            .execute_graph_cb(graph, inputs, true, fake_callback(), fake_escape())
            .await?;
        assert_eq!(outputs[&TryInto::try_into("out")?], Value::Int(5));
        Ok(())
    }

    #[tokio::test]
    async fn test_loop() -> anyhow::Result<()> {
        let stopval = 3;

        let [input, output] = Graph::boundary();
        let lt_graph = {
            let mut builder = GraphBuilder::new();

            let lt = builder.add_node("ilt")?;
            let stop_val = builder.add_node(Value::Int(stopval))?;

            builder.add_edge((input, "number"), (lt, "a"), None)?;
            builder.add_edge((stop_val, "value"), (lt, "b"), None)?;
            builder.add_edge((lt, "value"), (output, "pred"), None)?;

            builder.build()?
        };

        let break_graph = {
            let mut builder = GraphBuilder::new();
            let makest = builder.add_node("make_struct")?;
            builder.add_edge((input, "number"), (makest, "iter"), None)?;
            builder.add_edge((input, "accum"), (makest, "final"), None)?;

            let brk = builder.add_node(Node::Tag(Label::break_()))?;
            builder.add_edge((makest, "struct"), (brk, "value"), None)?;
            builder.add_edge((brk, "value"), (output, "value"), None)?;
            builder.build()?
        };

        let update_graph = {
            let mut builder = GraphBuilder::new();
            let numbers = builder.add_node("copy")?;
            builder.add_edge((input, "number"), (numbers, "value"), None)?;
            let makest = builder.add_node("make_struct")?;

            let add1 = builder.add_node("iadd")?;
            let increment = builder.add_node(Value::Int(1))?;
            builder.add_edge((numbers, "value_0"), (add1, "b"), None)?;
            builder.add_edge((increment, "value"), (add1, "a"), None)?;
            builder.add_edge((add1, "value"), (makest, "number"), None)?;

            let add2 = builder.add_node("iadd")?;
            builder.add_edge((input, "accum"), (add2, "a"), None)?;
            builder.add_edge((numbers, "value_1"), (add2, "b"), None)?;
            builder.add_edge((add2, "value"), (makest, "accum"), None)?;

            let update = builder.add_node(Node::Tag(Label::continue_()))?;
            builder.add_edge((makest, "struct"), (update, "value"), None)?;
            builder.add_edge((update, "value"), (output, "value"), None)?;

            builder.build()?
        };

        let body_graph = {
            let mut builder = GraphBuilder::new();
            let inputs = builder.add_node("unpack_struct")?;
            builder.add_edge((input, Label::value()), (inputs, "struct"), None)?;
            let switch = builder.add_node("switch")?;
            let copy = builder.add_node("copy")?;
            let eval = builder.add_node("eval")?;
            let condition = builder.add_node(Node::local_box(lt_graph))?;
            let update = builder.add_node(Value::Graph(update_graph))?;
            let return_ = builder.add_node(Value::Graph(break_graph))?;

            builder.add_edge((inputs, "number"), (copy, "value"), None)?;
            builder.add_edge((copy, "value_0"), (condition, "number"), None)?;

            builder.add_edge((update, "value"), (switch, "if_true"), None)?;
            builder.add_edge((return_, "value"), (switch, "if_false"), None)?;
            builder.add_edge((condition, "pred"), (switch, "pred"), None)?;

            builder.add_edge((switch, "value"), (eval, "thunk"), None)?;
            builder.add_edge((inputs, "accum"), (eval, "accum"), None)?;
            builder.add_edge((copy, "value_1"), (eval, "number"), None)?;

            builder.add_edge((eval, "value"), (output, "value"), None)?;

            builder.build()?
        };
        let graph = {
            let mut builder = GraphBuilder::new();
            let init = builder.add_node("make_struct")?;
            builder.add_edge((input, "initial"), (init, "number"), None)?;
            builder.add_edge((input, "extra"), (init, "accum"), None)?;

            let loop_ = builder.add_node("loop")?;
            builder.add_edge((init, "struct"), (loop_, Label::value()), None)?;

            let body = builder.add_node(Value::Graph(body_graph))?;

            builder.add_edge((body, "value"), (loop_, "body"), None)?;

            let outs = builder.add_node("unpack_struct")?;
            builder.add_edge((loop_, Label::value()), (outs, "struct"), None)?;

            builder.add_edge((outs, "iter"), (output, "iter"), None)?;
            builder.add_edge((outs, "final"), (output, "final"), None)?;
            builder.build()?
        };

        let python = ExternalWorker::new_spawn(python_path(), fake_interceptor()).await?;
        let runtime = Runtime::builder()
            .with_worker(python, py_loc())
            .await?
            .start();

        async fn run_loop(
            runtime: &Runtime,
            graph: crate::Graph,
            initial: i64,
            extra: i64,
        ) -> anyhow::Result<(i64, i64)> {
            let inputs = HashMap::from([
                (TryInto::try_into("initial")?, Value::Int(initial)),
                (TryInto::try_into("extra")?, Value::Int(extra)),
            ]);
            let outputs = runtime
                .execute_graph_cb(graph, inputs, true, fake_callback(), fake_escape())
                .await?;
            let iter = outputs.get(&TryInto::try_into("iter")?);
            let final_ = outputs.get(&TryInto::try_into("final")?);
            match (iter, final_, outputs.len()) {
                (Some(Value::Int(iter)), Some(Value::Int(final_)), 2) => Ok((*iter, *final_)),
                _ => bail!(
                    "Should have returned two ints iter&final, not {:?}",
                    outputs
                ),
            }
        }

        assert_eq!(run_loop(&runtime, graph.clone(), 1, 5).await?, (3, 8));

        assert_eq!(run_loop(&runtime, graph.clone(), -1, 0).await?, (3, 2));

        assert_eq!(run_loop(&runtime, graph.clone(), 5, 10).await?, (5, 10));

        Ok(())
    }

    // sequence unpair->pair to result in identity graph
    #[tokio::test]
    async fn test_sequence() -> anyhow::Result<()> {
        let [input, output] = Graph::boundary();
        let unpack = {
            let mut builder = GraphBuilder::new();

            let unpack = builder.add_node("unpack_pair")?;

            builder.add_edge((input, "p"), (unpack, "pair"), None)?;
            builder.add_edge((unpack, "first"), (output, "f"), None)?;
            builder.add_edge((unpack, "second"), (output, "s"), None)?;

            builder.build()?
        };

        let pack = {
            let mut builder = GraphBuilder::new();
            let pack = builder.add_node("make_pair")?;

            builder.add_edge((input, "f"), (pack, "first"), None)?;
            builder.add_edge((input, "s"), (pack, "second"), None)?;
            builder.add_edge((pack, "pair"), (output, "p"), None)?;

            builder.build()?
        };

        let seq_eval = {
            let mut builder = GraphBuilder::new();
            let c1 = builder.add_node(Node::Const(Value::Graph(unpack)))?;
            let c2 = builder.add_node(Node::Const(Value::Graph(pack)))?;
            let seq = builder.add_node("sequence")?;

            builder.add_edge((c1, "value"), (seq, "first"), None)?;
            builder.add_edge((c2, "value"), (seq, "second"), None)?;

            let eval = builder.add_node("eval")?;

            builder.add_edge((seq, "sequenced"), (eval, "thunk"), None)?;
            builder.add_edge((input, "p"), (eval, "p"), None)?;
            builder.add_edge((eval, "p"), (output, "p"), None)?;

            builder.build()?
        };

        let runtime = Runtime::builder().start();

        let mut inputs = HashMap::new();
        inputs.insert(
            TryInto::try_into("p")?,
            Value::Pair(Box::new((Value::Int(1), Value::Str("word".into())))),
        );

        let outputs = runtime
            .execute_graph_cb(
                seq_eval,
                inputs.clone(),
                true,
                fake_callback(),
                fake_escape(),
            )
            .await
            .unwrap();
        assert_eq!(outputs, inputs);

        Ok(())
    }

    // Multithreaded tests. Prior to PR #160 which introduced the test and fixed the runtime,
    // each of these were failing (nondeterministically) about 50% of the time. Putting
    // the body of the test inside a loop doesn't seem to change that, one must add a new test
    // with '#[tokio::test(flavor="multi_thread")] async fn' to get another roll of the die.
    fn discard_return() -> Result<Graph, GraphBuilderError> {
        let mut builder = GraphBuilder::new();
        let [input, output] = Graph::boundary();

        builder.add_edge((input, "keep"), (output, "res"), None)?;
        let disc = builder.add_node("discard")?;
        builder.add_edge((input, "ignore"), (disc, "value"), None)?;
        builder.build()
    }

    #[tokio::test(flavor = "multi_thread")]
    async fn test_box() -> anyhow::Result<()> {
        let outer = {
            let mut builder = GraphBuilder::new();
            let [input, output] = Graph::boundary();

            let inner = builder.add_node(Node::local_box(discard_return()?))?;
            let cst5 = builder.add_node(Value::Int(5))?;
            builder.add_edge((cst5, Label::value()), (inner, "keep"), None)?;
            builder.add_edge((input, "arg"), (inner, "ignore"), None)?;
            builder.add_edge((inner, "res"), (output, "value"), None)?;
            builder.build()?
        };

        let runtime = Runtime::builder().start();
        let inputs = HashMap::from([(TryInto::try_into("arg")?, Value::Float(3.1))]);
        let expected_outputs = HashMap::from([(TryInto::try_into("value")?, Value::Int(5))]);

        let outputs = runtime
            .execute_graph_cb(outer, inputs.clone(), true, fake_callback(), fake_escape())
            .await?;
        assert_eq!(outputs, expected_outputs);

        Ok(())
    }

    #[tokio::test(flavor = "multi_thread")]
    async fn test_partial() -> anyhow::Result<()> {
        let outer = {
            let mut builder = GraphBuilder::new();
            let [input, output] = Graph::boundary();

            let inner = builder.add_node(Value::Graph(discard_return()?))?;
            let cst5 = builder.add_node(Value::Int(5))?;

            let part = builder.add_node("partial")?;
            builder.add_edge((inner, Label::value()), (part, Label::thunk()), None)?;
            builder.add_edge((cst5, Label::value()), (part, "keep"), None)?;

            let ev = builder.add_node("eval")?;
            builder.add_edge((part, Label::value()), (ev, "thunk"), None)?;
            builder.add_edge((input, "arg"), (ev, "ignore"), None)?;
            builder.add_edge((ev, "res"), (output, "value"), None)?;
            builder.build()?
        };

        let runtime = Runtime::builder().start();
        let inputs = HashMap::from([(TryInto::try_into("arg")?, Value::Float(3.1))]);
        let expected_outputs = HashMap::from([(TryInto::try_into("value")?, Value::Int(5))]);

        let outputs = runtime
            .execute_graph_cb(outer, inputs, true, fake_callback(), fake_escape())
            .await?;
        assert_eq!(outputs, expected_outputs);

        Ok(())
    }

    // unpack and repack a Struct
    #[tokio::test]
    async fn test_struct() -> anyhow::Result<()> {
        let graph = {
            let mut builder = GraphBuilder::new();
            let [input, output] = Graph::boundary();

            let unpack = builder.add_node("unpack_struct")?;
            let pack = builder.add_node("make_struct")?;

            builder.add_edge((input, "st"), (unpack, "struct"), None)?;
            builder.add_edge((unpack, "x"), (pack, "x"), None)?;
            builder.add_edge((unpack, "y"), (pack, "y"), None)?;
            builder.add_edge((pack, "struct"), (output, "st"), None)?;

            builder.build()?
        };

        let runtime = Runtime::builder().start();
        let mut fields = HashMap::new();
        fields.insert(TryInto::try_into("x")?, Value::Int(1));
        fields.insert(TryInto::try_into("y")?, Value::Float(2.3));

        let mut inputs = HashMap::new();
        inputs.insert(TryInto::try_into("st")?, Value::Struct(fields));

        let outputs = runtime
            .execute_graph_cb(graph, inputs.clone(), true, fake_callback(), fake_escape())
            .await
            .unwrap();
        assert_eq!(outputs, inputs);

        Ok(())
    }

    // unpack and repack a Struct
    #[tokio::test]
    async fn test_map() -> anyhow::Result<()> {
        let graph = {
            let mut builder = GraphBuilder::new();
            let [input, output] = Graph::boundary();

            let insert = builder.add_node("insert_key")?;
            let remove = builder.add_node("remove_key")?;
            let copy = builder.add_node("copy")?;

            builder.add_edge((input, "mp"), (insert, "map"), None)?;
            builder.add_edge((input, "v"), (insert, "val"), None)?;
            builder.add_edge((input, "k"), (copy, "value"), None)?;
            builder.add_edge((copy, "value_0"), (insert, "key"), None)?;

            builder.add_edge((insert, "map"), (remove, "map"), None)?;
            builder.add_edge((copy, "value_1"), (remove, "key"), None)?;
            builder.add_edge((remove, "map"), (output, "mp"), None)?;
            builder.add_edge((remove, "val"), (output, "vl"), None)?;

            builder.build()?
        };

        let runtime = Runtime::builder().start();
        let mut map = HashMap::new();
        map.insert(Value::Str("x".into()), Value::Float(2.3));

        let insert_key = Value::Str("y".into());
        let insert_val = Value::Float(1.2);

        let mut inputs = HashMap::new();
        inputs.insert(TryInto::try_into("mp")?, Value::Map(map.clone()));
        inputs.insert(TryInto::try_into("k")?, insert_key);
        inputs.insert(TryInto::try_into("v")?, insert_val.clone());

        let outputs = runtime
            .execute_graph_cb(graph, inputs.clone(), true, fake_callback(), fake_escape())
            .await
            .unwrap();

        let mut expected_outputs = HashMap::new();
        expected_outputs.insert(TryInto::try_into("mp")?, Value::Map(map));
        expected_outputs.insert(TryInto::try_into("vl")?, insert_val);
        assert_eq!(outputs, expected_outputs);

        Ok(())
    }

    #[tokio::test]
    async fn test_equality() -> anyhow::Result<()> {
        let graph = {
            let mut builder = GraphBuilder::new();
            let [input, output] = Graph::boundary();

            let equality = builder.add_node("eq")?;

            builder.add_edge((input, "v0"), (equality, "value_0"), None)?;
            builder.add_edge((input, "v1"), (equality, "value_1"), None)?;

            builder.add_edge((equality, "result"), (output, "p"), None)?;

            builder.build()?
        };

        let runtime = Runtime::builder().start();

        let mut inputs = HashMap::new();
        inputs.insert(TryInto::try_into("v0")?, Value::Int(1));
        inputs.insert(TryInto::try_into("v1")?, Value::Int(1));

        let outputs = runtime
            .execute_graph_cb(
                graph.clone(),
                inputs.clone(),
                true,
                fake_callback(),
                fake_escape(),
            )
            .await
            .unwrap();

        assert_eq!(
            outputs.get(&TryInto::try_into("p")?),
            Some(&Value::Bool(true))
        );

        let mut inputs = HashMap::new();
        inputs.insert(TryInto::try_into("v0")?, Value::Str("foo".into()));
        inputs.insert(TryInto::try_into("v1")?, Value::Str("foof".into()));

        let outputs = runtime
            .execute_graph_cb(graph, inputs.clone(), true, fake_callback(), fake_escape())
            .await
            .unwrap();

        assert_eq!(
            outputs.get(&TryInto::try_into("p")?),
            Some(&Value::Bool(false))
        );
        Ok(())
    }

    // Parallel of simple graphs with node name clash
    #[tokio::test]
    async fn test_parallel() -> anyhow::Result<()> {
        let [input, output] = Graph::boundary();
        let graph1 = {
            let mut builder = GraphBuilder::new();

            let c1 = builder.add_node(Node::Const(Value::Int(1)))?;
            let add = builder.add_node("iadd")?;

            builder.add_edge((c1, "value"), (add, "b"), None)?;
            builder.add_edge((input, "vl"), (add, "a"), None)?;
            builder.add_edge((add, "value"), (output, "vl"), None)?;

            builder.build()?
        };

        let graph2 = {
            let mut builder = GraphBuilder::new();
            let c1 = builder.add_node(Node::Const(Value::Str("word2".into())))?;
            builder.add_edge((input, "vr"), (output, "vr_0"), None)?;
            builder.add_edge((c1, "value"), (output, "vr_1"), None)?;

            builder.build()?
        };

        let graph_par = {
            let mut builder = GraphBuilder::new();

            let c1 = builder.add_node(Node::Const(Value::Graph(graph1)))?;
            let c2 = builder.add_node(Node::Const(Value::Graph(graph2)))?;
            let par = builder.add_node("parallel")?;
            let eval = builder.add_node("eval")?;

            builder.add_edge((c1, "value"), (par, "left"), None)?;
            builder.add_edge((c2, "value"), (par, "right"), None)?;
            builder.add_edge((par, "value"), (eval, "thunk"), None)?;
            builder.add_edge((input, "value_0"), (eval, "vl"), None)?;
            builder.add_edge((input, "value_1"), (eval, "vr"), None)?;
            builder.add_edge((eval, "vl"), (output, "value_0"), None)?;
            builder.add_edge((eval, "vr_0"), (output, "value_1"), None)?;
            builder.add_edge((eval, "vr_1"), (output, "value_2"), None)?;

            builder.build()?
        };

        let runtime = Runtime::builder().start();

        let inputs = HashMap::from([
            (TryInto::try_into("value_0")?, Value::Int(2)),
            (TryInto::try_into("value_1")?, Value::Str("word".into())),
        ]);

        let outputs = runtime
            .execute_graph_cb(graph_par, inputs, true, fake_callback(), fake_escape())
            .await?;

        assert_eq!(
            outputs.get(&TryInto::try_into("value_0")?),
            Some(&Value::Int(3))
        );
        assert_eq!(
            outputs.get(&TryInto::try_into("value_1")?),
            Some(&Value::Str("word".into()))
        );
        assert_eq!(
            outputs.get(&TryInto::try_into("value_2")?),
            Some(&Value::Str("word2".into()))
        );

        Ok(())
    }

    #[tokio::test]
    async fn test_map_builtin() -> anyhow::Result<()> {
        let [input, output] = Graph::boundary();
        let thunk = {
            let mut builder = GraphBuilder::new();

            let c1 = builder.add_node(Node::Const(Value::Int(2)))?;
            let mul = builder.add_node("imul")?;

            builder.add_edge((c1, Label::value()), (mul, "b"), None)?;
            builder.add_edge((input, Label::value()), (mul, "a"), None)?;
            builder.add_edge((mul, Label::value()), (output, Label::value()), None)?;

            builder.build()?
        };

        let graph = {
            let mut builder = GraphBuilder::new();

            let c1 = builder.add_node(Node::Const(Value::Graph(thunk)))?;
            let map = builder.add_node("map")?;

            builder.add_edge((c1, Label::value()), (map, Label::thunk()), None)?;
            builder.add_edge((input, Label::value()), (map, Label::value()), None)?;
            builder.add_edge((map, Label::value()), (output, Label::value()), None)?;

            builder.build()?
        };

        let input_vec = Value::Vec(vec![Value::Int(1), Value::Int(2), Value::Int(3)]);

        let runtime = Runtime::builder().start();

        let inputs = HashMap::from([(Label::value(), input_vec)]);

        let outputs = runtime
            .execute_graph_cb(graph, inputs, true, fake_callback(), fake_escape())
            .await?;

        println!("{:?}", outputs);

        assert_eq!(
            outputs.get(&Label::value()),
            Some(&Value::Vec(vec![
                Value::Int(2),
                Value::Int(4),
                Value::Int(6)
            ]))
        );

        Ok(())
    }

    #[tokio::test]
    async fn test_map_concurrent() -> anyhow::Result<()> {
        let [input, output] = Graph::boundary();
        let thunk = {
            let mut builder = GraphBuilder::new();

            let c1 = builder.add_node(Value::Float(1.0))?;
            let sleep = builder.add_node("sleep")?;

            builder.add_edge((c1, Label::value()), (sleep, "delay_secs"), None)?;
            builder.add_edge((input, Label::value()), (sleep, Label::value()), None)?;
            builder.add_edge((sleep, Label::value()), (output, Label::value()), None)?;

            builder.build()?
        };

        let graph = {
            let mut builder = GraphBuilder::new();

            let c1 = builder.add_node(Node::Const(Value::Graph(thunk)))?;
            let map = builder.add_node("map")?;

            builder.add_edge((c1, Label::value()), (map, Label::thunk()), None)?;
            builder.add_edge((input, Label::value()), (map, Label::value()), None)?;
            builder.add_edge((map, Label::value()), (output, Label::value()), None)?;

            builder.build()?
        };

        let input_vec = Value::Vec(vec![
            Value::Int(1),
            Value::Int(2),
            Value::Int(3),
            Value::Int(4),
            Value::Int(5),
        ]);

        let runtime = Runtime::builder()
            .with_worker(
                ExternalWorker::new_spawn(python_path(), fake_interceptor()).await?,
                py_loc(),
            )
            .await?
            .start();

        let inputs = HashMap::from([(Label::value(), input_vec)]);

        let earlier = std::time::Instant::now();

        let outputs = runtime
            .execute_graph_cb(graph, inputs, true, fake_callback(), fake_escape())
            .await?;

        assert!(earlier.elapsed() < Duration::from_millis(1250));
        assert_eq!(
            outputs.get(&Label::value()),
            Some(&Value::Vec(vec![
                Value::Int(1),
                Value::Int(2),
                Value::Int(3),
                Value::Int(4),
                Value::Int(5)
            ]))
        );

        Ok(())
    }

    #[fixture]
    fn div_graph() -> anyhow::Result<Graph> {
        let mut builder = GraphBuilder::new();
        let [input, output] = Graph::boundary();

        let div = builder.add_node("idiv")?;
        builder.add_edge((input, "a"), (div, "a"), None)?;
        builder.add_edge((input, "b"), (div, "b"), None)?;
        builder.add_edge((div, "value"), (output, "value"), None)?;
        let graph = builder.build()?;
        Ok(graph)
    }

    #[rstest]
    #[tokio::test]
    async fn test_idiv_op(div_graph: anyhow::Result<Graph>) -> anyhow::Result<()> {
        let graph = div_graph?;

        let runtime = Runtime::builder().start();

        let inputs = HashMap::from([
            (TryInto::try_into("a")?, Value::Int(10)),
            (TryInto::try_into("b")?, Value::Int(2)),
        ]);

        let outputs = runtime
            .execute_graph_cb(graph, inputs, true, fake_callback(), fake_escape())
            .await?;

        assert_eq!(
            outputs.get(&TryInto::try_into("value")?),
            Some(&Value::Int(5))
        );

        Ok(())
    }

    #[rstest]
    #[tokio::test]
    #[should_panic(expected = "Tried to divide by zero")]
    async fn test_idiv_zero(div_graph: anyhow::Result<Graph>) {
        let graph = div_graph.unwrap();

        let runtime = Runtime::builder().start();

        let inputs = HashMap::from([
            (TryInto::try_into("a").unwrap(), Value::Int(10)),
            (TryInto::try_into("b").unwrap(), Value::Int(0)),
        ]);

        runtime
            .execute_graph_cb(graph, inputs, true, fake_callback(), fake_escape())
            .await
            .unwrap();
    }

    #[fixture]
    fn mod_graph() -> anyhow::Result<Graph> {
        let mut builder = GraphBuilder::new();
        let [input, output] = Graph::boundary();

        let mod_ = builder.add_node("imod")?;
        builder.add_edge((input, "a"), (mod_, "a"), None)?;
        builder.add_edge((input, "b"), (mod_, "b"), None)?;
        builder.add_edge((mod_, "value"), (output, "value"), None)?;
        let graph = builder.build()?;
        Ok(graph)
    }

    #[rstest]
    #[tokio::test]
    async fn test_imod_op(mod_graph: anyhow::Result<Graph>) -> anyhow::Result<()> {
        let graph = mod_graph?;

        let runtime = Runtime::builder().start();

        let inputs = HashMap::from([
            (TryInto::try_into("a")?, Value::Int(10)),
            (TryInto::try_into("b")?, Value::Int(3)),
        ]);

        let outputs = runtime
            .execute_graph_cb(graph, inputs, true, fake_callback(), fake_escape())
            .await?;

        assert_eq!(
            outputs.get(&TryInto::try_into("value")?),
            Some(&Value::Int(1))
        );

        Ok(())
    }

    #[rstest]
    #[tokio::test]
    #[should_panic(expected = "Tried to take modulus with zero.")]
    async fn test_imod_zero(mod_graph: anyhow::Result<Graph>) {
        let graph = mod_graph.unwrap();

        let runtime = Runtime::builder().start();

        let inputs = HashMap::from([
            (TryInto::try_into("a").unwrap(), Value::Int(10)),
            (TryInto::try_into("b").unwrap(), Value::Int(0)),
        ]);

        runtime
            .execute_graph_cb(graph, inputs, true, fake_callback(), fake_escape())
            .await
            .unwrap();
    }

    #[tokio::test]
    async fn test_loc_merge() -> anyhow::Result<()> {
        let py_loc_2: LocationName = TryInto::try_into("python2")?;
        let python_1 = ExternalWorker::new_spawn(&python_path(), fake_interceptor()).await?;
        let python_2 = python_1.clone();
        let runtime = Runtime::builder()
            .with_worker(python_1, py_loc())
            .await?
            .with_worker(python_2, py_loc_2)
            .await?
            .start();

        let sig = runtime.signature().root;
        assert_eq!(
            sig.functions[&(TryInto::try_into("copy")?)].locations,
            vec![Location::local()]
        );
        assert_eq!(
            sig.subspaces[&(TryInto::try_into("python_nodes")?)].functions
                [&(TryInto::try_into("id_py")?)]
                .locations,
            vec![Location(vec![py_loc()]), Location(vec![py_loc_2])]
        );
        Ok(())
    }

    #[tokio::test]
    async fn test_loc_clash() -> anyhow::Result<()> {
        let python_1 = ExternalWorker::new_spawn(&python_path(), fake_interceptor()).await?;
        let python_2 = python_1.clone();

        let builder = Runtime::builder()
            .with_worker(python_1, py_loc())
            .await?
            .with_worker(python_2, py_loc())
            .await;
        match builder {
            Ok(_) => bail!("Builder should fail with two workers on the same location"),
            Err(e) => {
                assert_eq!(
                    e.to_string(),
                    anyhow::Error::from(LocationConflict(py_loc())).to_string()
                );
                Ok(())
            }
        }
    }

    #[tokio::test]
    async fn test_stack_trace_map_eval() -> anyhow::Result<()> {
        use anyhow::anyhow;
        let (func_node, func_graph) = {
            let mut builder = GraphBuilder::new();
            let [input, output] = Graph::boundary();

            let nod = builder.add_node("st_test")?;
            builder.add_edge((input, "argument"), (nod, "label"), None)?;
            builder.add_edge((nod, "labelled_trace"), (output, "result"), None)?;
            (nod, builder.build()?)
        };
        let (eval_node, map_thunk) = {
            let mut builder = GraphBuilder::new();
            let [input, output] = Graph::boundary();
            let func_cst = builder.add_node(Node::Const(Value::Graph(func_graph)))?;
            let eval_node = builder.add_node("eval")?;
            builder.add_edge((func_cst, "value"), (eval_node, "thunk"), None)?;
            builder.add_edge((input, "value"), (eval_node, "argument"), None)?;
            builder.add_edge((eval_node, "result"), (output, "value"), None)?;
            (eval_node, builder.build()?)
        };
        let (map_node, graph) = {
            let mut builder = GraphBuilder::new();
            let [input, output] = Graph::boundary();
            let map_func = builder.add_node(Node::Const(Value::Graph(map_thunk)))?;
            let map_node = builder.add_node("map")?;
            builder.add_edge((map_func, "value"), (map_node, "thunk"), None)?;
            builder.add_edge((input, "elems"), (map_node, "value"), None)?;
            builder.add_edge((map_node, "value"), (output, "mapped"), None)?;
            (map_node, builder.build()?)
        };

        let arg: Label = TryInto::try_into("label").unwrap();
        let res: Label = TryInto::try_into("labelled_trace").unwrap();
        let mut t = GraphType::new();
        t.add_input(arg, Type::Str);
        t.add_output(res, Type::Str);
        let mut worker = LocalWorker::new();
        let n = tierkreis_core::prelude::TryFrom::try_from("st_test").unwrap();
        worker.add_function(
            FunctionName::builtin(n),
            FunctionDeclaration {
                type_scheme: t.into(),
                description: "Compare stack trace with expected string".into(),
                input_order: vec![arg],
                output_order: vec![res],
            },
            move || {
                RuntimeOperation::new_fn_simple(move |mut inputs, context| {
                    let Value::Str(s) = inputs.remove_entry(&arg).unwrap().1 else {
                        return Err(anyhow!("bad input"));
                    };
                    Ok(HashMap::from([(
                        res,
                        Value::Str(format!("{s} {:?}", context.graph_trace)),
                    )]))
                })
            },
        );
        let runtime = Runtime::builder()
            .with_local_functions(worker)
            .unwrap()
            .start();

        runtime.infer_type(&graph).unwrap();
        let input_elems = vec![Value::Str("a".into()), Value::Str("b".into())];

        let res = runtime
            .execute_graph_cb(
                graph.clone(),
                HashMap::from([(TryInto::try_into("elems").unwrap(), Value::Vec(input_elems))]),
                true,
                fake_callback(),
                fake_escape(),
            )
            .await
            .unwrap();
        let trace_for_elem = |i| {
            Into::<GraphTrace>::into(
                GraphTrace::Root
                    .inner_node(map_node)
                    .list_elem(i)
                    .inner_node(eval_node)
                    .inner_node(func_node),
            )
        };
        let expected = HashMap::from([(
            TryInto::try_into("mapped").unwrap(),
            Value::Vec(vec![
                Value::Str(format!("a {:?}", trace_for_elem(0))),
                Value::Str(format!("b {:?}", trace_for_elem(1))),
            ]),
        )]);
        assert_eq!(res, expected);
        Ok(())
    }
}
