use super::{FunctionWorker, RuntimeWorker, Worker};
use crate::operations::RuntimeOperation;
use crate::RunGraphError;
use anyhow::{anyhow, Context};
use hyper_util::rt::TokioIo;
use std::collections::HashMap;
use std::ffi::OsStr;
use std::process::Stdio;
use std::sync::Arc;
use tierkreis_core::graph::{Graph, Value};
use tierkreis_core::namespace::Signature;
use tierkreis_core::prelude::TryInto;
use tierkreis_core::symbol::{FunctionName, Label, Location};
use tierkreis_proto::messages::{
    self as proto_messages, Callback, JobHandle, NodeTrace, RunGraphResponse,
};
use tierkreis_proto::protos_gen::v1alpha1::runtime as proto_runtime;
use tierkreis_proto::protos_gen::v1alpha1::signature as proto_sig;
use tierkreis_proto::protos_gen::v1alpha1::worker as proto_worker;
use tierkreis_proto::ConvertError;
use tokio::io::{AsyncBufReadExt, BufReader};
use tokio::net::UnixStream;
use tokio::process::Child;
use tokio::process::Command;
use tonic::async_trait;
use tonic::service::Interceptor;
use tonic::transport::{Channel, Endpoint, Uri};
use tracing::instrument;
/// Worker for functions implemented in external processes.
#[derive(Clone)]
struct Connection {
    channel: Channel,
    interceptor: ClientInterceptor,

    /// Keep a handle to the child process so that it is not killed.
    #[allow(dead_code)]
    process: Option<Arc<Child>>,
}

/// Connection to an external worker (perhaps a Tierkreis server),
/// that can execute `run_function` for some defined+reported set of functions.
#[derive(Clone)]
pub struct ExternalWorker {
    connection: Connection,
    /// Cached signature
    signature: Signature,
}

/// Forwards `run_graph` requests; used to route these from a worker back to the
/// server (ancestor) which issued the `run_function` request (to that worker).
pub struct CallbackForwarder(Connection);

/// A link in a forwarding chain - forwards `run_function` calls to a destination,
/// passing a [Location] which uniquely identifies the chain and the next link therein
/// (typically by the location being unique to each source/caller).
// TODO consider moving Location into Connection
#[derive(Clone)]
pub struct FunctionForwarder(Connection, Location);

/// Used for forwarding "escape hatch" calls (a `run_function` sent from a child runtime
/// back to an ancestor).
#[derive(Clone)]
pub struct EscapeHatch {
    /// The next link "above" this runtime, or None if
    /// the forwarding chain ends here (nowhere further to escape to).
    parent: Option<FunctionForwarder>,
    /// Tells other workers ("below") how to access the chain here,
    /// i.e. becomes the next link for such children.
    this_runtime: Callback,
}

/// Placeholder for future code that adds authentication data to a client request
#[derive(Clone, Debug, Default)]
pub enum AuthInjector {
    /// No authentication data to add
    #[default]
    NoAuth,
    /// token and key metadata to add
    #[allow(missing_docs)]
    TokenKey { token: String, key: String },
}

/// Placeholder [Interceptor] that just adds some authentication (meta)data.
#[derive(Clone, Debug, Default)]
pub struct ClientInterceptor {
    /// Authentication data to add.
    pub auther: AuthInjector,
}

impl ClientInterceptor {
    /// Create a new instance to add specified authentication metadata
    pub fn new(auther: AuthInjector) -> Self {
        Self { auther }
    }
}

impl Interceptor for ClientInterceptor {
    fn call(&mut self, mut req: tonic::Request<()>) -> Result<tonic::Request<()>, tonic::Status> {
        match &self.auther {
            AuthInjector::NoAuth => Ok(req),
            AuthInjector::TokenKey { token, key } => {
                req.metadata_mut().insert("token", token.parse().unwrap());
                req.metadata_mut().insert("key", key.parse().unwrap());
                Ok(req)
            }
        }
    }
}

impl Connection {
    /// Spawn a process given an external command, and connect. See [FunctionForwarder::new_spawn],
    /// although we do not request signature here.
    #[instrument(
        name="starting external worker process"
        skip(command, interceptor),
        fields(command = &*command.as_ref().to_string_lossy()))]
    async fn new_spawn(
        command: impl AsRef<OsStr>,
        interceptor: ClientInterceptor,
    ) -> anyhow::Result<Self> {
        // Spawn the python subprocess
        let mut process = Command::new(command.as_ref())
            .stdout(Stdio::piped())
            .stderr(Stdio::inherit())
            .kill_on_drop(true)
            .spawn()
            .with_context(|| "failed to spawn worker process")?;

        tracing::debug!("Spawned external worker process.");

        // Wait for the child to write the path of the unix socket to stdout. If the worker process
        // stops this will also fail with an error. After the line is received we drop the stdout
        // handle, so the pipe is closed as we no longer need it.
        // TODO: Maybe a timeout for this?
        let socket_path = BufReader::new(process.stdout.take().unwrap())
            .lines()
            .next_line()
            .await
            .with_context(|| "failed to receive socket path from worker process")
            .unwrap()
            .ok_or_else(|| anyhow!("worker process did not send socket path"))
            .unwrap();

        tracing::debug!("Received unix domain socket path from python worker.");
        // Open a communication channel for the socket path. We need to supply some uri here since the
        // API is weird, but it is arbitrary and not used.
        let channel = Endpoint::new("http://[::]:50051")?
            .connect_with_connector(tower::service_fn({
                let socket_path = socket_path.clone();
                move |_: Uri| {
                    let socket_path = socket_path.clone();
                    async move {
                        Ok::<_, std::io::Error>(TokioIo::new(
                            UnixStream::connect(socket_path).await?,
                        ))
                    }
                }
            }))
            .await
            .with_context(|| "failed to connect to the socket of the python worker")?;

        tracing::info!("Connected to spawned worker's grpc server.");

        Ok(Self {
            channel,
            process: Some(Arc::new(process)),
            interceptor,
        })
    }

    #[instrument(
        name="connecting to external worker"
        skip(uri, interceptor),
        fields(uri = uri.to_string().as_str())
    )]
    async fn new_connect(uri: &Uri, interceptor: ClientInterceptor) -> anyhow::Result<Self> {
        let channel = Endpoint::from(uri.clone())
            .connect()
            .await
            .with_context(|| format!("failed to connect to worker at uri {}", uri))?;

        tracing::info!(
            uri = uri.to_string().as_str(),
            "Connected to the worker's grpc server."
        );

        Ok(Self {
            channel,
            process: None,
            interceptor,
        })
    }

    #[instrument(
        name = "run external function",
        fields(otel.kind = "client", _node_trace = node_trace.as_ref().map_or(String::new(), ToString::to_string)),
        skip(self, inputs, node_trace, callback)
    )]
    async fn run_function(
        &self,
        function: FunctionName,
        inputs: HashMap<Label, Value>,
        loc: Location,
        callback: Callback,
        node_trace: Option<NodeTrace>,
        job_handle: Option<JobHandle>,
    ) -> anyhow::Result<HashMap<Label, Value>> {
        let mut request = proto_messages::RunFunctionRequest::new(function, inputs, loc, callback);
        let node_str = node_trace
            .as_ref()
            .map(|nt| nt.to_string())
            .unwrap_or_else(|| "None".to_string());
        if let Some(node_trace) = node_trace {
            request.set_node_trace(node_trace);
        }

        if let Some(job_id) = job_handle {
            request.set_job_id(job_id.into_inner().0);
        }

        let mut worker_client = proto_worker::worker_client::WorkerClient::with_interceptor(
            self.channel.clone(),
            self.interceptor.clone(),
        );

        let response = worker_client.run_function(inject_trace(request)).await;
        if let Err(e) = &response {
            tracing::info!(
                error = e.to_string(),
                node = node_str,
                "failed to run function in worker."
            );
        }
        let response = response
            .context("failed to run function in worker")?
            .into_inner();

        tracing::debug!("received response from worker");

        let outputs = TryInto::try_into(response.outputs.unwrap_or_default())
            .context("failed to parse function outputs from worker response")?;

        Ok(outputs)
    }

    async fn run_graph(
        &self,
        graph: Graph,
        inputs: HashMap<Label, Value>,
        loc: Location,
        type_check: bool,
        escape: Option<Callback>,
    ) -> Result<HashMap<Label, Value>, RunGraphError> {
        let request = proto_messages::RunGraphRequest {
            graph,
            inputs,
            loc,
            type_check,
            escape,
        };

        let mut runtime_client = proto_runtime::runtime_client::RuntimeClient::with_interceptor(
            self.channel.clone(),
            self.interceptor.clone(),
        );

        let resp: RunGraphResponse = TryInto::try_into(
            runtime_client
                .run_graph(inject_trace(request))
                .await
                .context("failed to run graph in scope")?
                .into_inner(),
        )
        .map_err(|e: ConvertError| anyhow!(e))?;

        match resp {
            RunGraphResponse::Success(x) => Ok(x),
            RunGraphResponse::TypeError(x) => Err(RunGraphError::TypeError(x)),
            RunGraphResponse::Error(x) => Err(RunGraphError::RuntimeError(Arc::new(anyhow!(x)))),
        }
    }

    async fn get_signature(
        &self,
        loc: Location,
    ) -> anyhow::Result<proto_sig::ListFunctionsResponse> {
        let mut signature_client = proto_sig::signature_client::SignatureClient::with_interceptor(
            self.channel.clone(),
            self.interceptor.clone(),
        );

        // Retrieve the worker's signature
        tracing::debug!("Retrieving signature for worker.");
        let signature = signature_client
            .list_functions(inject_trace(proto_messages::ListFunctionsRequest { loc }))
            .await
            .context("failed to retrieve signature from worker")?
            .into_inner();

        Ok(signature)
    }

    async fn type_check(
        &self,
        value: Value,
        loc: Location,
    ) -> anyhow::Result<proto_sig::InferTypeResponse> {
        let mut tc_client = proto_sig::type_inference_client::TypeInferenceClient::with_interceptor(
            self.channel.clone(),
            self.interceptor.clone(),
        );

        tracing::debug!("Type checking on worker.");
        let resp = tc_client
            .infer_type(inject_trace(proto_messages::InferTypeRequest {
                value,
                loc,
            }))
            .await
            .context("failed to infer type on worker")?
            .into_inner();

        Ok(resp)
    }

    fn spawn(&self, function: &FunctionName, loc: &Location) -> RuntimeOperation {
        let function = function.clone();
        let loc = loc.clone();
        let this = self.clone();
        RuntimeOperation::new_fn_async(move |inputs, context| async move {
            let _ = &context;
            this.run_function(
                function,
                inputs,
                loc,
                context.callback,
                Some(context.graph_trace.as_node_trace()?),
                context.checkpoint_client.map(|ch| ch.job_handle),
            )
            .await
        })
    }
}

#[async_trait]
impl RuntimeWorker for Connection {
    async fn execute_graph(
        &self,
        graph: Graph,
        inputs: HashMap<Label, Value>,
        location: Location,
        type_check: bool,
        escape: Option<Callback>,
    ) -> Result<HashMap<Label, Value>, RunGraphError> {
        self.run_graph(graph, inputs, location, type_check, escape)
            .await
    }

    fn spawn_graph(&self, graph: Graph, location: &Location) -> RuntimeOperation {
        let this = self.clone();
        let loc = location.clone();
        RuntimeOperation::new_fn_async(move |inputs, context| async move {
            let _ = &context;
            match this
                .run_graph(graph, inputs, loc, false, Some(context.escape.this_runtime))
                .await
            {
                Ok(x) => Ok(x),
                Err(RunGraphError::TypeError(x)) => Err(anyhow!("Type errors: {}", x)),
                Err(RunGraphError::RuntimeError(x)) => Err(anyhow!(x)),
            }
        })
    }

    async fn infer_type(
        &self,
        to_check: Value,
        location: Location,
    ) -> anyhow::Result<proto_sig::InferTypeResponse> {
        self.type_check(to_check, location).await
    }
}

impl ExternalWorker {
    async fn from_connection(connection: Connection) -> anyhow::Result<Self> {
        let signature = TryInto::try_into(connection.get_signature(Location::local()).await?)?;
        Ok(Self {
            connection,
            signature,
        })
    }

    /// Spawn a process that runs the specified command, which must print out the socket address
    /// for a GRPC server as the first line of stdout. (We expect the command to start a new gRPC
    /// server in its own process.)
    ///
    /// The socket address could be a hostname + port, or path to a UNIX filesystem socket.
    ///
    /// `new_spawn` then connects to the worker's gRPC server and requests its signature.
    pub async fn new_spawn(
        command: impl AsRef<OsStr>,
        interceptor: ClientInterceptor,
    ) -> anyhow::Result<Self> {
        let connection = Connection::new_spawn(command, interceptor).await?;
        Self::from_connection(connection).await
    }

    /// Connects to an already-running external process given its Uri
    pub async fn new_connect(uri: &Uri, interceptor: ClientInterceptor) -> anyhow::Result<Self> {
        let connection = Connection::new_connect(uri, interceptor).await?;
        Self::from_connection(connection).await
    }
}

#[async_trait]
impl FunctionWorker for ExternalWorker {
    fn spawn(&self, function: &FunctionName, loc: &Location) -> RuntimeOperation {
        self.connection.spawn(function, loc)
    }
}

#[async_trait]
impl Worker for ExternalWorker {
    async fn signature(
        &self,
        location: Location,
    ) -> anyhow::Result<proto_sig::ListFunctionsResponse> {
        if location == Location::local() {
            Ok(self.signature.clone().into())
        } else {
            self.connection.get_signature(location).await
        }
    }

    fn to_runtime_worker(&self) -> Option<&dyn RuntimeWorker> {
        if self.signature.scopes.is_empty() {
            None
        } else {
            Some(&self.connection)
        }
    }
}

impl CallbackForwarder {
    // It would be easy to implement new_spawn, but it doesn't really make sense
    // - we are forwarding callbacks from a worker back to the already-existing
    // server that issued the original request to that worker.

    /// Connects to a remote Tierkreis server in order to forward callbacks onto it
    pub async fn new_connect(uri: &Uri, interceptor: ClientInterceptor) -> anyhow::Result<Self> {
        Ok(Self(Connection::new_connect(uri, interceptor).await?))
    }

    /// Gets the signature (list of known functions + namespaces) of the server
    pub async fn signature(
        &self,
        location: Location,
    ) -> anyhow::Result<proto_sig::ListFunctionsResponse> {
        self.0.get_signature(location).await
    }

    /// Allows running graphs (/typechecking) by forwarding requests
    pub fn as_runtime_worker(&self) -> &dyn RuntimeWorker {
        &self.0
    }
}

impl FunctionForwarder {
    /// Creates a new instance that forwards requests to a Uri, identifying itself
    /// with a Location
    pub async fn new(
        uri: &Uri,
        interceptor: ClientInterceptor,
        loc: Location,
    ) -> anyhow::Result<Self> {
        // TODO it probably only makes sense if `loc` has exactly one LocationName.
        // Should we enforce that?
        let conn = Connection::new_connect(uri, interceptor).await?;
        Ok(Self(conn, loc))
    }

    /// Forwards a call to run a function up the chain.
    /// `loc` specifies the Location relative to the root of the forwarding chain.
    pub async fn fwd_run_function(
        &self,
        function: FunctionName,
        inputs: HashMap<Label, Value>,
        loc: Location,
        callback: Callback,
        node_trace: Option<NodeTrace>,
    ) -> anyhow::Result<HashMap<Label, Value>> {
        self.0
            .run_function(
                function,
                inputs,
                // We expect self.1 to be a single LocationName identifying the route
                // to the root, which then uses Location `loc` (untouched)
                self.1.clone().concat(&loc),
                callback,
                node_trace,
                None,
            )
            .await
    }
    fn spawn(&self, function: &FunctionName) -> RuntimeOperation {
        self.0.spawn(function, &self.1)
    }
}

impl EscapeHatch {
    /// An instance whereby `run_function`s execute on this runtime,
    /// given a Callback telling child workers how to connect to this runtime.
    pub fn this_runtime(target: Callback) -> Self {
        Self::new(None, target)
    }

    /// Creates a new instance from a Callback to this runtime and optionally a parent.
    /// If `parent` is non-null, then `this_runtime` should identify `parent`
    /// in the servers EscapeHatch-forwarding map.
    pub fn new(parent: Option<FunctionForwarder>, this_runtime: Callback) -> Self {
        Self {
            this_runtime,
            parent,
        }
    }

    /// Cross-fingers that this runs a function.
    /// Deliberately no way to specify a location.
    pub fn spawn_escape(&self, function: FunctionName) -> Option<RuntimeOperation> {
        // Note that the Connection will include the OperationContext's callback
        // (perhaps to this runtime) in the run_function request it issues.
        self.parent.as_ref().map(|ff| ff.spawn(&function))
    }
}

fn inject_trace<R, T>(request: R) -> tonic::Request<T>
where
    R: tonic::IntoRequest<T>,
{
    use opentelemetry::propagation::TextMapPropagator;
    use opentelemetry_http::HeaderInjector;
    use opentelemetry_sdk::propagation::TraceContextPropagator;
    use tracing_opentelemetry::OpenTelemetrySpanExt;

    let mut request = request.into_request();

    let mut headers = std::mem::take(request.metadata_mut()).into_headers();
    let span = tracing::Span::current();
    let context = span.context();

    let propagator = TraceContextPropagator::new();
    propagator.inject_context(&context, &mut HeaderInjector(&mut headers));

    *request.metadata_mut() = tonic::metadata::MetadataMap::from_headers(headers);
    request
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::tests::{fake_callback, fake_escape, fake_interceptor, py_loc};
    use std::error::Error;
    use std::{collections::HashMap, time::Duration};
    use tierkreis_core::namespace::Signature;
    use tierkreis_core::prelude::TryInto;
    use tierkreis_core::symbol::{Location, Name, Prefix};
    use tokio::join;

    #[tokio::test]
    async fn simple_snippet() -> Result<(), Box<dyn Error + Send + Sync>> {
        let python = format!(
            "{}/../python/tests/test_worker/main.py",
            env!("CARGO_MANIFEST_DIR")
        );
        let python = ExternalWorker::new_spawn(python, fake_interceptor()).await?;

        let mut inputs = HashMap::new();
        inputs.insert(TryInto::try_into("a")?, Value::Int(2));
        inputs.insert(TryInto::try_into("b")?, Value::Int(3));

        let outputs = python
            .connection
            .run_function(
                "python_nodes::python_add".parse()?,
                inputs,
                Location::local(),
                fake_callback(),
                None,
                None,
            )
            .await?;

        assert_eq!(outputs.get(&Label::value()), Some(&Value::Int(5)));

        Ok(())
    }

    #[tokio::test]
    async fn test_mistyped_worker() -> Result<(), Box<dyn Error + Send + Sync>> {
        use crate::Runtime;
        use tierkreis_core::graph::GraphBuilder;

        let python = format!(
            "{}/../python/tests/test_worker/main.py",
            env!("CARGO_MANIFEST_DIR")
        );

        let py_worker: ExternalWorker =
            ExternalWorker::new_spawn(python, fake_interceptor()).await?;
        let runtime = Runtime::builder()
            .with_worker(py_worker, py_loc())
            .await?
            .start();

        let graph = {
            let mut builder = GraphBuilder::new();
            let [input, output] = tierkreis_core::graph::Graph::boundary();

            let bad_op = builder.add_node("python_nodes::mistyped_op")?;
            builder.add_edge((input, "i"), (bad_op, "inp"), None)?;
            builder.add_edge((bad_op, "value"), (output, "res"), None)?;
            builder.build()?
        };

        let inputs = HashMap::from([(TryInto::try_into("i")?, Value::Int(6))]);

        let err = runtime
            .execute_graph_cb(graph, inputs, true, fake_callback(), fake_escape())
            .await
            .expect_err("Should detect runtime type mismatch");
        // TODO worker function does not propagate internal betterproto
        // conversion error (expects integer and finds float)
        assert!(format!("{:?}", err).contains("failed to run function in worker"));
        Ok(())
    }

    #[tokio::test]
    async fn concurrent_nodes() -> Result<(), Box<dyn Error + Send + Sync>> {
        let python = format!(
            "{}/../python/tests/test_worker/main.py",
            env!("CARGO_MANIFEST_DIR")
        );
        let python_1 = ExternalWorker::new_spawn(&python, fake_interceptor()).await?;
        let python_2 = python_1.clone();

        let mut inputs_1 = HashMap::new();
        inputs_1.insert(TryInto::try_into("wait")?, Value::Int(1));
        inputs_1.insert(Label::value(), Value::Int(0));

        let mut inputs_2 = HashMap::new();
        inputs_2.insert(TryInto::try_into("wait")?, Value::Int(1));
        inputs_2.insert(Label::value(), Value::Int(1));

        let earlier = std::time::Instant::now();

        let fut_1 = python_1.connection.run_function(
            "python_nodes::id_delay".parse()?,
            inputs_1,
            Location::local(),
            fake_callback(),
            None,
            None,
        );
        let fut_2 = python_2.connection.run_function(
            "python_nodes::id_delay".parse()?,
            inputs_2,
            Location::local(),
            fake_callback(),
            None,
            None,
        );

        // We need to use `join!` instead of awaiting in sequence to make sure the futures
        // are both polled simultaneously.
        let (result_1, result_2) = join!(fut_1, fut_2);

        let outputs_1 = result_1?;
        let outputs_2 = result_2?;

        let now = std::time::Instant::now();

        assert!(now.duration_since(earlier) < Duration::from_millis(1250));
        assert_eq!(outputs_1[&Label::value()], Value::Int(0));
        assert_eq!(outputs_2[&Label::value()], Value::Int(1));

        Ok(())
    }

    #[tokio::test]
    async fn check_external_location() -> Result<(), Box<dyn Error + Send + Sync>> {
        let python = format!(
            "{}/../python/tests/test_worker/main.py",
            env!("CARGO_MANIFEST_DIR")
        );
        let python = ExternalWorker::new_spawn(&python, fake_interceptor()).await?;
        let pn: Prefix = TryInto::try_into("python_nodes")?;
        let name: Name = TryInto::try_into("id_py")?;
        let sig: Signature = TryInto::try_into(python.signature(Location::local()).await?)?;
        let item = &sig.root.subspaces[&pn].functions[&name];
        assert_eq!(item.locations, vec![Location(vec![])]);
        Ok(())
    }
}
