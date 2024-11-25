//! GRPC Server management

use crate::{server::TierkreisServer, ServerError};
use async_trait::async_trait;
use futures::Future;
use futures_core::Stream;
use tokio::net::{TcpListener, TcpStream};
// use hyper::server::accept::Accept;
// use hyper::server::conn::{AddrIncoming, AddrStream};

use std::pin::Pin;
use std::task::{Context, Poll};
use tierkreis_core::prelude::TryInto;
use tierkreis_proto::protos_gen::v1alpha1::jobs as pj;
use tierkreis_proto::protos_gen::v1alpha1::runtime as pr;
use tierkreis_proto::protos_gen::v1alpha1::signature as ps;
use tierkreis_proto::protos_gen::v1alpha1::worker as pw;
use tonic::{transport::Server, Request, Response};
use tonic_health::ServingStatus;

// This "TcpIncoming" borrows heavily from that of hyperium/tonic.
// https://github.com/hyperium/tonic/pull/1037 attempts to make theirs public.
// Their code is under MIT License but we do not believe that this constitutes
// a "substantial portion" and so we do not have to distribute the MIT License with it.
struct TcpIncoming {
    pub inner: TcpListener,
}

impl Stream for TcpIncoming {
    type Item = Result<TcpStream, std::io::Error>;

    fn poll_next(mut self: Pin<&mut Self>, cx: &mut Context<'_>) -> Poll<Option<Self::Item>> {
        Pin::new(&mut self.inner)
            .poll_accept(cx)
            .map(|x| Some(x.map(|(s, _)| s)))
    }
}

/// Starts a GRPC [RuntimeServer] listening on the given [TcpListener] stream.
///
/// [RuntimeServer]: pr::runtime_server::RuntimeServer
pub async fn start_run_graph_server(
    server: TierkreisServer,
    // This could be parametrized as much as the serve_with_incoming_shutdown method below,
    // but for now this is as general as we need.
    incoming: TcpListener,
    shutdown: impl Future<Output = ()> + Send + 'static,
) -> anyhow::Result<()> {
    let server = RuntimeServer::new(server);
    let (mut health_reporter, health_service) = tonic_health::server::health_reporter();

    health_reporter
        .set_service_status("", ServingStatus::Serving)
        .await;

    let incoming = TcpIncoming { inner: incoming };
    Server::builder()
        .trace_fn(trace_fn)
        .add_service(health_service)
        .add_service(pr::runtime_server::RuntimeServer::new(server.clone()))
        .add_service(pw::worker_server::WorkerServer::new(server.clone()))
        .add_service(ps::signature_server::SignatureServer::new(server.clone()))
        .add_service(ps::type_inference_server::TypeInferenceServer::new(server))
        .serve_with_incoming_shutdown(incoming, shutdown)
        .await?;
    Ok(())
}

/// Starts a GRPC [JobControlServer] listening on the given [TcpListener] stream.
///
/// [JobControlServer]: pj::job_control_server::JobControlServer
pub async fn start_job_server(
    server: TierkreisServer,
    incoming: TcpListener,
    shutdown: impl Future<Output = ()> + Send + 'static,
) -> anyhow::Result<()> {
    let server = JobControlServer { server };
    let (mut health_reporter, health_service) = tonic_health::server::health_reporter();

    health_reporter
        .set_service_status("", ServingStatus::Serving)
        .await;

    let incoming = TcpIncoming { inner: incoming };
    Server::builder()
        .trace_fn(trace_fn)
        .add_service(health_service)
        .add_service(ps::signature_server::SignatureServer::new(server.clone()))
        .add_service(pj::job_control_server::JobControlServer::new(server))
        .serve_with_incoming_shutdown(incoming, shutdown)
        .await?;
    Ok(())
}

fn trace_fn(request: &http::Request<()>) -> tracing::Span {
    use opentelemetry::propagation::TextMapPropagator;
    use opentelemetry_http::HeaderExtractor;
    use opentelemetry_sdk::propagation::TraceContextPropagator;
    use tracing_opentelemetry::OpenTelemetrySpanExt;

    let span = tracing::info_span!(
        "serving grpc request",
        otel.kind = "server",
        service.name = "tierkreis",
    );

    let propagator = TraceContextPropagator::new();
    let parent = propagator.extract(&HeaderExtractor(request.headers()));
    span.set_parent(parent);

    span
}

#[derive(Clone)]
struct JobControlServer {
    server: TierkreisServer,
}

#[async_trait]
impl pj::job_control_server::JobControl for JobControlServer {
    async fn running_jobs(
        &self,
        request: Request<pj::RunningJobsRequest>,
    ) -> Result<Response<pj::RunningJobsResponse>, tonic::Status> {
        let request = request.into_inner().into();

        let response = self.server.running_jobs(request).await.into();

        Ok(Response::new(response))
    }

    async fn start_job(
        &self,
        request: Request<pj::StartJobRequest>,
    ) -> Result<Response<pj::StartJobResponse>, tonic::Status> {
        let request = TryInto::try_into(request.into_inner()).map_err(ServerError::Parse)?;

        let response = self.server.start_job(request).await.into();

        Ok(Response::new(response))
    }

    async fn job_status(
        &self,
        request: Request<pj::JobStatusRequest>,
    ) -> Result<Response<pj::JobStatusResponse>, tonic::Status> {
        let request = TryInto::try_into(request.into_inner()).map_err(ServerError::Parse)?;

        let response = self.server.job_status(request).await?.into();

        Ok(Response::new(response))
    }

    async fn stop_job(
        &self,
        request: Request<pj::StopJobRequest>,
    ) -> Result<Response<pj::StopJobResponse>, tonic::Status> {
        let request = TryInto::try_into(request.into_inner()).map_err(ServerError::Parse)?;

        let response = self.server.stop_job(request).await?.into();

        Ok(Response::new(response))
    }

    async fn delete_completed(
        &self,
        _request: Request<pj::DeleteCompletedRequest>,
    ) -> Result<Response<pj::DeleteCompletedResponse>, tonic::Status> {
        let response = self.server.delete_completed().await.into();

        Ok(Response::new(response))
    }
}

#[async_trait]
impl ps::signature_server::Signature for JobControlServer {
    async fn list_functions(
        &self,
        request: Request<ps::ListFunctionsRequest>,
    ) -> Result<Response<ps::ListFunctionsResponse>, tonic::Status> {
        list_functions(&self.server, request).await
    }
}

#[derive(Clone)]
struct RuntimeServer {
    server: TierkreisServer,
}

impl RuntimeServer {
    pub fn new(server: TierkreisServer) -> Self {
        Self { server }
    }
}

#[async_trait]
impl pr::runtime_server::Runtime for RuntimeServer {
    async fn run_graph(
        &self,
        request: tonic::Request<pr::RunGraphRequest>,
    ) -> Result<tonic::Response<pr::RunGraphResponse>, tonic::Status> {
        let request = TryInto::try_into(request.into_inner()).map_err(ServerError::Parse)?;

        let response = self.server.run_graph(request).await.into();

        Ok(Response::new(response))
    }
}

#[async_trait]
impl pw::worker_server::Worker for RuntimeServer {
    async fn run_function(
        &self,
        request: Request<pw::RunFunctionRequest>,
    ) -> Result<Response<pw::RunFunctionResponse>, tonic::Status> {
        let request = TryInto::try_into(request).map_err(ServerError::Parse)?;

        let response = self.server.run_function(request).await?.into();

        Ok(Response::new(response))
    }
}

async fn list_functions(
    server: &TierkreisServer,
    request: Request<ps::ListFunctionsRequest>,
) -> Result<Response<ps::ListFunctionsResponse>, tonic::Status> {
    let request = TryInto::try_into(request.into_inner()).map_err(ServerError::Parse)?;

    let response = server
        .list_functions(request)
        .await
        .map_err(|e| tonic::Status::unknown(e.to_string()))?;

    Ok(Response::new(response))
}

#[async_trait]
impl ps::signature_server::Signature for RuntimeServer {
    async fn list_functions(
        &self,
        request: Request<ps::ListFunctionsRequest>,
    ) -> Result<Response<ps::ListFunctionsResponse>, tonic::Status> {
        list_functions(&self.server, request).await
    }
}

#[async_trait]
impl ps::type_inference_server::TypeInference for RuntimeServer {
    async fn infer_type(
        &self,
        request: Request<ps::InferTypeRequest>,
    ) -> Result<Response<ps::InferTypeResponse>, tonic::Status> {
        let request = TryInto::try_into(request.into_inner()).map_err(ServerError::Parse)?;

        let response = self
            .server
            .infer_type(request)
            .await
            .map_err(|e| tonic::Status::unknown(e.to_string()))?;

        Ok(Response::new(response))
    }
}

impl From<ServerError> for tonic::Status {
    fn from(error: ServerError) -> Self {
        match error {
            ServerError::Parse(_) => tonic::Status::invalid_argument(error.to_string()),
            ServerError::UnknownFunction(_) => tonic::Status::not_found(error.to_string()),
            ServerError::Internal => tonic::Status::internal(error.to_string()),
        }
    }
}
