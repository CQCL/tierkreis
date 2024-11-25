//! Server executable that handles GRPC requests using a Tierkreis Runtime

use std::fs::read_to_string;
use std::path::PathBuf;
use std::time::Duration;

use clap::Parser;
use futures::FutureExt;
// use hyper::server::conn::http1::AddrIncoming;
use opentelemetry::KeyValue;
use opentelemetry_otlp::WithExportConfig;
use opentelemetry_sdk::trace::Config;
use serde::Deserialize;
use serde_with::serde_as;
use serde_with::DisplayFromStr;
use thiserror::Error;
use tierkreis_core::symbol::{FunctionName, LocationName};
use tierkreis_proto::ConvertError;
use tierkreis_runtime::RuntimeTypeChecking;
use tierkreis_runtime::{
    workers::{ClientInterceptor, ExternalWorker},
    Runtime,
};
use tokio::net::TcpListener;
use tonic::transport::Uri;
use tracing::{instrument, Instrument};
use tracing_subscriber::filter::LevelFilter;
use tracing_subscriber::fmt;
use tracing_subscriber::layer::SubscriberExt;
use tracing_subscriber::util::SubscriberInitExt;

use crate::server::TierkreisServer;

pub mod grpc;
pub mod server;

fn default_host() -> String {
    "127.0.0.1".to_string()
}

/// Describes a worker that should be started in a new process
#[serde_as]
#[derive(Deserialize, Clone, Debug)]
pub struct LocPathBuf {
    /// Location that graphs will be able to use to refer to the worker
    #[serde_as(as = "DisplayFromStr")]
    pub location: LocationName,
    /// Path in local filesystem to worker code (a directory that must contain `main.py`)
    pub path: PathBuf,
}

/// Describes an already-running worker to which the server should connect
#[serde_as]
#[derive(Deserialize, Clone, Debug)]
pub struct LocUri {
    /// Location that graphs will be able to use to refer to the worker    
    #[serde_as(as = "DisplayFromStr")]
    pub location: LocationName,
    /// Uri to which the server should connect
    #[serde_as(as = "DisplayFromStr")]
    pub uri: Uri,
}

/// All configuration options with which a new server can be started
#[serde_as]
#[derive(Deserialize, Clone, Debug)]
pub struct TierkreisConfig {
    /// Hostname on which to listen
    #[serde(default = "default_host")]
    pub host: String,

    /// Port on which to listen for GRPC requests
    pub port: u16,

    /// May contain an endpoint to which Opentelemetry data
    /// will be exported, e.g. "http://localhost:4317"
    pub telemetry: Option<String>,

    /// Path to a local worker executable.
    #[serde(default)]
    worker_path: Vec<LocPathBuf>,

    /// URI of remote worker servers.
    #[serde(default)]
    worker_uri: Vec<LocUri>,

    #[serde(default)]
    runtime_type_checking: RuntimeTypeChecking,

    /// Whether to start as a JobControl server rather than run graph server.
    #[serde(default)]
    job_server: bool,

    /// Optional endpoint for recording checkpoints from JobControl server only
    checkpoint_endpoint: Option<(String, u16)>,

    /// Tracing level, default is "Info".
    #[serde(default)]
    tracing_level: TracingLevel,
}

#[derive(Deserialize, Clone, Debug, Default)]
enum TracingLevel {
    Off,
    Error,
    Warn,
    #[default]
    Info,
    Debug,
    Trace,
}

impl From<TracingLevel> for LevelFilter {
    fn from(level: TracingLevel) -> Self {
        match level {
            TracingLevel::Off => LevelFilter::OFF,
            TracingLevel::Error => LevelFilter::ERROR,
            TracingLevel::Warn => LevelFilter::WARN,
            TracingLevel::Info => LevelFilter::INFO,
            TracingLevel::Debug => LevelFilter::DEBUG,
            TracingLevel::Trace => LevelFilter::TRACE,
        }
    }
}

impl TierkreisConfig {
    fn load(json: &str) -> serde_json::Result<Self> {
        serde_json::from_str(json)
    }
}

#[derive(Parser)]
#[clap(name = "Tierkreis Server")]
#[clap(version = "0.1")]
#[clap(group = clap::ArgGroup::new("config-group").multiple(false).required(true))]
struct Args {
    #[clap(long, short = 'c', group = "config-group")]
    config: Option<String>,
    #[clap(long, short = 'C', group = "config-group")]
    config_file: Option<PathBuf>,
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let args = Args::parse();
    let config_str = if let Some(x) = args.config {
        x
    } else if let Some(x) = args.config_file {
        read_to_string(x)?
    } else {
        unreachable!()
    };
    let config = TierkreisConfig::load(&config_str)?;
    setup_tracing(config.clone())?;
    run_servers(config).await?;
    opentelemetry::global::shutdown_tracer_provider();
    Ok(())
}

fn setup_tracing(config: TierkreisConfig) -> anyhow::Result<()> {
    use opentelemetry::global::set_text_map_propagator;
    use opentelemetry::trace::TracerProvider;
    use opentelemetry_sdk::propagation::TraceContextPropagator;
    use opentelemetry_sdk::trace;
    use opentelemetry_sdk::Resource;

    set_text_map_propagator(TraceContextPropagator::new());

    let mut otlp = None;

    if let Some(otlp_endpoint) = config.telemetry {
        let otlp_exporter = opentelemetry_otlp::new_exporter()
            .tonic()
            .with_endpoint(otlp_endpoint)
            .with_timeout(Duration::from_secs(3));

        let tracer = opentelemetry_otlp::new_pipeline()
            .tracing()
            .with_exporter(otlp_exporter)
            .with_trace_config(
                Config::default()
                    .with_resource(Resource::new(vec![KeyValue::new(
                        "service.name",
                        "tierkreis",
                    )]))
                    .with_sampler(trace::Sampler::AlwaysOn),
            )
            .install_batch(opentelemetry_sdk::runtime::Tokio)?
            .tracer("tierkreis");

        otlp = Some(tracing_opentelemetry::layer().with_tracer(tracer));
    };

    let fmt = fmt::layer().with_writer(std::io::stderr);

    tracing_subscriber::registry()
        .with(fmt)
        .with(otlp)
        .with(LevelFilter::from(config.tracing_level))
        .try_init()?;

    Ok(())
}

#[instrument(
    name = "starting runtime",
    skip(worker_paths, worker_uris, interceptor)
)]
async fn start_runtime(
    worker_paths: &Vec<LocPathBuf>,
    worker_uris: &Vec<LocUri>,
    interceptor: ClientInterceptor,
    runtime_type_checking: tierkreis_runtime::RuntimeTypeChecking,
) -> anyhow::Result<Runtime> {
    let mut runtime = Runtime::builder();

    for x in worker_paths {
        let (loc, mut path) = (x.location, x.path.clone());
        path.push("main.py");
        let worker = ExternalWorker::new_spawn(path.as_os_str(), interceptor.clone()).await?;
        runtime = runtime.with_worker(worker, loc).await?;
    }
    for x in worker_uris {
        let (loc, uri) = (x.location, &x.uri);
        let worker = ExternalWorker::new_connect(uri, interceptor.clone()).await?;
        runtime = runtime.with_worker(worker, loc).await?;
    }

    runtime = runtime.with_checking(runtime_type_checking);

    Ok(runtime.start())
}

#[instrument(skip(config))]
async fn run_servers(config: TierkreisConfig) -> anyhow::Result<()> {
    let interceptor = ClientInterceptor::default();

    let runtime = start_runtime(
        &config.worker_path,
        &config.worker_uri,
        interceptor.clone(),
        config.runtime_type_checking,
    )
    .await?;

    let callback_uri: Uri = format!("http://{}:{}", config.host, config.port).parse()?;

    let mut servers = Vec::new();

    let host_port = format!("{}:{}", config.host, config.port);
    let addr: String = host_port.parse().unwrap();
    // let incoming = {
    //     // let mut ai = AddrIncoming::bind(&addr)?;
    //     let mut listener =  TcpListener::bind(addr).await?;
    //     listener.set_keepalive(None);
    //     let (mut ai, _) = listener.accept().await?;
    //     ai.set_nodelay(true);
    //     // ai.set_keepalive(None);
    //     ai
    // };
    let incoming = TcpListener::bind(addr).await?;
    if config.job_server {
        tracing::info!("Starting JobControl server");
        let server = TierkreisServer::new(
            runtime,
            interceptor,
            callback_uri,
            config.checkpoint_endpoint.clone(),
        );

        servers.push(tokio::spawn(async move {
            let _ = &config;
            grpc::start_job_server(
                server,
                incoming,
                tokio::signal::ctrl_c().map(|_| {
                    println!("SubmitJob server shutdown complete.");
                }),
            )
            .instrument(tracing::info_span!(
                "submit server",
                net.host.name = config.host.as_str(),
                net.host.port = config.port,
            ))
            .await?;
            anyhow::Ok(())
        }));
    } else {
        tracing::info!("Starting RunGraph server");
        let server = TierkreisServer::new(runtime, interceptor, callback_uri, None);

        servers.push(tokio::spawn(async move {
            let _ = &config;
            grpc::start_run_graph_server(
                server,
                incoming,
                tokio::signal::ctrl_c().map(|_| {
                    println!("Run graph server shutdown complete.");
                }),
            )
            .instrument(tracing::info_span!(
                "run graph server",
                net.host.name = config.host.as_str(),
                net.host.port = config.port,
            ))
            .await?;
            anyhow::Ok(())
        }));
    }

    println!("Server started");

    let _ = futures::future::join_all(servers).await;
    Ok(())
}

/// An error in the interface to [TierkreisServer]
/// (as opposed to the [Runtime] beneath)
///
/// [Runtime]: tierkreis_runtime::Runtime
#[derive(Debug, Error)]
pub enum ServerError {
    /// An error in parsing the input protobuf
    #[error("failed to parse the input: {0}")]
    Parse(ConvertError),

    /// A function name passed to [TierkreisServer::run_function] was not found
    #[error("unknown function: {0}")]
    UnknownFunction(FunctionName),

    /// Catch-all/unspecified other internal error
    #[error("Tierkreis internal server error")]
    Internal,
}

impl warp::reject::Reject for ServerError {}

impl warp::reply::Reply for ServerError {
    fn into_response(self) -> warp::reply::Response {
        use warp::http::StatusCode;
        let status = match &self {
            ServerError::Parse(_) => StatusCode::BAD_REQUEST,
            ServerError::UnknownFunction(_) => StatusCode::NOT_FOUND,
            ServerError::Internal => StatusCode::INTERNAL_SERVER_ERROR,
        };
        warp::reply::with_status(self.to_string(), status).into_response()
    }
}
