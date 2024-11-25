//! Crate versions of [JobControl], [RunGraph] and [RunFunction] messages
//! with conversion routines, and also PyO3 interface.
//!
//! [JobControl]: pj::job_control_server::JobControl
//! [RunGraph]: pr::runtime_server::Runtime::run_graph
//! [RunFunction]: pw::worker_server::Worker::run_function

use crate::{
    protos_gen::v1alpha1::controller as pc, protos_gen::v1alpha1::jobs as pj,
    protos_gen::v1alpha1::runtime as pr, protos_gen::v1alpha1::signature as ps,
    protos_gen::v1alpha1::worker as pw, ConvertError,
};
use anyhow::anyhow;
use http::Uri;
// rexport for encoding in other workspace crates
pub use prost::Message;
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use std::{collections::HashMap, str::FromStr};
use thiserror::Error;
use tierkreis_core::graph::{Graph, TypeScheme, Value};
use tierkreis_core::prelude::{TryFrom, TryInto};
use tierkreis_core::symbol::{FunctionName, Label, Location};
use tierkreis_core::type_checker::TypeErrors;
use tonic::metadata::{Binary, MetadataKey, MetadataMap, MetadataValue};
use uuid::Uuid;
use warp::reject::Reject;

mod graph_trace;
pub use graph_trace::{GraphTrace, NodeTrace};

/// Status of concurrently running job - still running, or completed.
/// Related to [pj::JobStatus] but contains the final results to write into DB.
#[derive(Debug, Clone)]
pub enum Status {
    /// Still executing, no results yet (interface does not provide intermediates)
    Running,
    /// Job has finished, successfully or otherwise
    Completed(Completed),
}

/// Result of a completed job - success or error
pub type Completed = Result<Arc<HashMap<Label, Value>>, Arc<anyhow::Error>>;

/// Identifier for a job - Uuid and attempt number.
/// Crate version of [pj::JobHandle]
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub struct JobHandle {
    /// Nexus Job Uuid, identifies a request from a user to run a graph
    job_uuid: Uuid,
    /// Numbered attempt by a Tierkreis runtime to run that graph
    attempt: u32,
}

impl JobHandle {
    /// Gets the Uuid and attempt number as a tuple
    pub fn into_inner(self) -> (Uuid, u32) {
        (self.job_uuid, self.attempt)
    }

    /// Accessor to the job Uuid
    pub fn job_uuid(&self) -> &Uuid {
        self.job_uuid.as_ref()
    }
}

impl std::fmt::Display for JobHandle {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}-{}", self.job_uuid, self.attempt)
    }
}

impl TryFrom<pj::JobHandle> for JobHandle {
    type Error = ConvertError;

    fn try_from(value: pj::JobHandle) -> Result<Self, Self::Error> {
        let job_uuid = Uuid::from_str(&value.uuid).map_err(|_| ConvertError::ProtoError)?;
        let attempt = value.attempt_id;
        Ok(JobHandle { job_uuid, attempt })
    }
}

impl From<JobHandle> for pj::JobHandle {
    fn from(value: JobHandle) -> Self {
        pj::JobHandle {
            uuid: value.job_uuid.to_string(),
            attempt_id: value.attempt,
        }
    }
}

/// [JobControl::running_jobs] request to list the jobs that are running. (Empty!)
/// Crate version of [pj::RunningJobsRequest].
///
/// [JobControl::running_jobs]: pj::job_control_server::JobControl::running_jobs
#[derive(Debug, Clone)]
pub struct RunningJobsRequest;

impl From<pj::RunningJobsRequest> for RunningJobsRequest {
    fn from(_: pj::RunningJobsRequest) -> Self {
        RunningJobsRequest
    }
}

/// Response from [JobControl::running_jobs] listing the jobs that are running.
/// Crate version of [pj::RunningJobsResponse].
///
/// [JobControl::running_jobs]: pj::job_control_server::JobControl::running_jobs

#[derive(Debug, Clone)]
pub struct RunningJobsResponse {
    /// Every job started by [JobControl::start_job] not yet deleted by [JobControl::delete_completed]
    ///
    /// [JobControl::start_job]: pj::job_control_server::JobControl::start_job
    /// [JobControl::delete_completed]: pj::job_control_server::JobControl::delete_completed
    pub jobs: Vec<JobInfo>,
}

impl From<RunningJobsResponse> for pj::RunningJobsResponse {
    fn from(response: RunningJobsResponse) -> Self {
        pj::RunningJobsResponse {
            jobs: response.jobs.into_iter().map(pj::JobStatus::from).collect(),
        }
    }
}

/// [JobControl::stop_job] request to cancel (abort) execution of a job, usually issued
/// because the controller is planning to make a fresh attempt of the graph.
/// Crate version of [pj::StopJobRequest].
///
/// [JobControl::stop_job]: pj::job_control_server::JobControl::stop_job
#[derive(Debug, Clone)]
pub struct StopJobRequest {
    /// The Uuid of the job (all attempt numbers should be stopped)
    pub job_id: Uuid,
}

impl TryFrom<pj::StopJobRequest> for StopJobRequest {
    type Error = ConvertError;

    fn try_from(value: pj::StopJobRequest) -> Result<Self, Self::Error> {
        Ok(StopJobRequest {
            job_id: value.job_id.parse().map_err(|_| ConvertError::ProtoError)?,
        })
    }
}

/// Result of [JobControl::stop_job], i.e. empty.
/// Crate version of [pj::StopJobResponse]
///
/// [JobControl::stop_job]: pj::job_control_server::JobControl::stop_job
#[derive(Debug, Clone)]
pub struct StopJobResponse;

impl From<StopJobResponse> for pj::StopJobResponse {
    fn from(_: StopJobResponse) -> Self {
        pj::StopJobResponse {}
    }
}

/// [JobControl::stop_job] error that the job Uuid is unknown. Turned into a GPRC error.
///
/// [JobControl::stop_job]: pj::job_control_server::JobControl::stop_job
#[derive(Debug, Clone, Error)]
#[error("failed to delete unknown job: {0:?}")]
pub struct UnknownJob(pub Uuid);

impl From<UnknownJob> for tonic::Status {
    fn from(err: UnknownJob) -> Self {
        Self::not_found(err.to_string())
    }
}

impl Reject for UnknownJob {}

impl warp::reply::Reply for UnknownJob {
    fn into_response(self) -> warp::reply::Response {
        use warp::http::StatusCode;
        warp::reply::with_status(self.to_string(), StatusCode::NOT_FOUND).into_response()
    }
}

/// [JobControl::start_job] request to start a new attempt of a job Uuid to run a graph
///
/// [JobControl::start_job]: pj::job_control_server::JobControl::start_job
#[derive(Debug, Clone)]
pub struct StartJobRequest {
    /// The graph to run
    pub graph: Graph,
    /// The input to pass to the graph
    pub inputs: HashMap<Label, Value>,
    /// Identifier which may be polled via [JobControl::job_status] and/or used to report
    /// results to the checkpointing server
    ///
    /// [JobControl::job_status]: pj::job_control_server::JobControl::job_status
    pub job_handle: JobHandle,
}

impl TryFrom<pj::StartJobRequest> for StartJobRequest {
    type Error = ConvertError;

    fn try_from(value: pj::StartJobRequest) -> Result<Self, Self::Error> {
        Ok(StartJobRequest {
            graph: TryInto::try_into(value.graph.ok_or(ConvertError::ProtoError)?)?,
            inputs: TryInto::try_into(value.inputs.ok_or(ConvertError::ProtoError)?)?,
            job_handle: TryInto::try_into(value.job_handle.ok_or(ConvertError::ProtoError)?)?,
        })
    }
}

impl From<StartJobRequest> for pj::StartJobRequest {
    fn from(value: StartJobRequest) -> Self {
        pj::StartJobRequest {
            graph: Some(value.graph.into()),
            inputs: Some(value.inputs.into()),
            job_handle: Some(value.job_handle.into()),
        }
    }
}

impl tonic::IntoRequest<pj::StartJobRequest> for StartJobRequest {
    fn into_request(self) -> tonic::Request<pj::StartJobRequest> {
        let x: pj::StartJobRequest = self.into();
        x.into_request()
    }
}

/// Result of [JobControl::start_job] - success or failure in starting the job
///
/// [JobControl::start_job]: pj::job_control_server::JobControl::start_job
#[derive(Debug, Clone)]
pub enum StartJobResponse {
    /// Job successfully started, returns the [StartJobRequest::job_handle]
    JobId(JobHandle),
    /// Graph failed typechecking, execution not started
    TypeErrors(TypeErrors),
    /// Another error preventing the graph from starting (e.g. could not connect to
    /// checkpoint server, or the `StartJobRequest.job_handle` was already running).
    /// Does not include errors inside the graph itself (except deserialization), these
    /// are reported instead to the checkpoint server.
    RuntimeError(String),
}

impl From<StartJobResponse> for pj::StartJobResponse {
    fn from(response: StartJobResponse) -> Self {
        let result = match response {
            StartJobResponse::JobId(job_handle) => {
                pj::start_job_response::Result::JobHandle(job_handle.into())
            }
            StartJobResponse::TypeErrors(errors) => {
                pj::start_job_response::Result::TypeErrors(errors.into())
            }
            StartJobResponse::RuntimeError(e) => pj::start_job_response::Result::RuntimeError(e),
        };
        Self {
            result: Some(result),
        }
    }
}

// For use when we expect the graph to always typecheck (e.g. scoped execution)
impl TryFrom<pj::StartJobResponse> for JobHandle {
    type Error = ConvertError;

    fn try_from(value: pj::StartJobResponse) -> Result<Self, Self::Error> {
        match value.result.ok_or(ConvertError::ProtoError)? {
            pj::start_job_response::Result::JobHandle(job_handle) => {
                Ok(TryInto::try_into(job_handle)?)
            }
            pj::start_job_response::Result::TypeErrors(_)
            | pj::start_job_response::Result::RuntimeError(_) => Err(ConvertError::ProtoError),
        }
    }
}

/// [JobControl::job_status] request to poll a specific job uuid + attempt.
/// Crate version of [pj::JobStatusRequest].
///
/// [JobControl::job_status]: pj::job_control_server::JobControl::job_status
#[derive(Debug, Clone)]
#[allow(missing_docs)]
pub struct JobStatusRequest {
    pub handle: JobHandle,
}

impl TryFrom<pj::JobStatusRequest> for JobStatusRequest {
    type Error = ConvertError;

    fn try_from(value: pj::JobStatusRequest) -> Result<Self, Self::Error> {
        Ok(JobStatusRequest {
            handle: TryInto::try_into(value.handle.ok_or(ConvertError::ProtoError)?)?,
        })
    }
}

/// (Successful) result of [JobControl::job_status].
/// Crate version of [pj::JobStatusResponse].
///
/// [JobControl::job_status]: pj::job_control_server::JobControl::job_status
#[derive(Debug, Clone)]
#[allow(missing_docs)]
pub struct JobStatusResponse {
    pub job_info: JobInfo,
}

impl From<JobStatusResponse> for pj::JobStatusResponse {
    fn from(response: JobStatusResponse) -> Self {
        pj::JobStatusResponse {
            status: Some(response.job_info.into()),
        }
    }
}

/// Error for [JobControl::job_status] - will become a GRPC error.
///
/// [JobControl::job_status]: pj::job_control_server::JobControl::job_status
#[derive(Debug, Clone, Error)]
pub enum JobStatusError {
    /// The [JobStatusRequest::handle] was not known
    #[error("failed to retrieve unknown task: {0:?}")]
    UnknownTask(JobHandle),
}

impl From<JobStatusError> for tonic::Status {
    fn from(err: JobStatusError) -> Self {
        match err {
            JobStatusError::UnknownTask(_) => Self::not_found(err.to_string()),
        }
    }
}

impl Reject for JobStatusError {}

impl warp::reply::Reply for JobStatusError {
    fn into_response(self) -> warp::reply::Response {
        use warp::http::StatusCode;
        let status = match &self {
            JobStatusError::UnknownTask(_) => StatusCode::NOT_FOUND,
        };
        warp::reply::with_status(self.to_string(), status).into_response()
    }
}

/// Information on a single job, returned by [JobControl::running_jobs].
/// Crate version of [pj::JobStatus], but includes full results of a completed job.
///
/// [JobControl::running_jobs]: pj::job_control_server::JobControl::running_jobs]
#[derive(Debug, Clone)]
pub struct JobInfo {
    /// The handle of the running (or completed, but not yet deleted) job
    pub handle: JobHandle,
    /// Current status (result values or error message)
    pub status: Status,
}

impl From<JobInfo> for pj::JobStatus {
    fn from(task: JobInfo) -> Self {
        let status = match task.status {
            Status::Running => Some(pj::job_status::Status::Running(pj::Empty {})),
            Status::Completed(Ok(_)) => Some(pj::job_status::Status::Success(pj::Empty {})),
            Status::Completed(Err(result)) => {
                Some(pj::job_status::Status::Error(format!("{:?}", result)))
            }
        };

        pj::JobStatus {
            handle: Some(task.handle.into()),
            status,
        }
    }
}

/// Result of [JobControl::delete_completed] - a list of the jobs deleted.
/// Crate version of [pj::DeleteCompletedResponse]
///
/// [JobControl::delete_completed]: pj::job_control_server::JobControl::delete_completed
#[derive(Debug, Clone)]
pub struct DeleteCompletedResponse {
    /// All the deleted, completed, job identifiers
    pub deleted_jobs: Vec<JobHandle>,
}

impl From<DeleteCompletedResponse> for pj::DeleteCompletedResponse {
    fn from(response: DeleteCompletedResponse) -> Self {
        pj::DeleteCompletedResponse {
            job_handles: response
                .deleted_jobs
                .into_iter()
                .map(|x| x.into())
                .collect(),
        }
    }
}

/// Crate version of [ps::InferTypeRequest] for Rust-PYO3 interface
#[derive(Debug, Clone)]
#[allow(missing_docs)]
pub struct InferTypeRequest {
    pub value: Value,
    pub loc: Location,
}

impl TryFrom<ps::InferTypeRequest> for InferTypeRequest {
    type Error = ConvertError;

    fn try_from(value: ps::InferTypeRequest) -> Result<Self, Self::Error> {
        Ok(InferTypeRequest {
            value: TryInto::try_into(value.value.ok_or(ConvertError::ProtoError)?)?,
            loc: value
                .loc
                .map(TryInto::try_into)
                .transpose()?
                .unwrap_or_else(Location::local),
        })
    }
}

impl From<InferTypeRequest> for ps::InferTypeRequest {
    fn from(value: InferTypeRequest) -> Self {
        ps::InferTypeRequest {
            value: Some(value.value.into()),
            loc: Some(value.loc.into()),
        }
    }
}

impl tonic::IntoRequest<ps::InferTypeRequest> for InferTypeRequest {
    fn into_request(self) -> tonic::Request<ps::InferTypeRequest> {
        let req: ps::InferTypeRequest = self.into();
        req.into_request()
    }
}

/// Crate version of [ps::InferTypeResponse]
#[derive(Debug, Clone)]
#[allow(missing_docs)]
pub enum InferTypeResponse {
    Success {
        value: Value,
        type_scheme: TypeScheme,
    },
    Error {
        error: TypeErrors,
    },
}

impl From<Result<(TypeScheme, Value), TypeErrors>> for InferTypeResponse {
    fn from(result: Result<(TypeScheme, Value), TypeErrors>) -> Self {
        match result {
            Ok((type_scheme, value)) => InferTypeResponse::Success { type_scheme, value },
            Err(error) => InferTypeResponse::Error { error },
        }
    }
}

impl From<InferTypeResponse> for ps::InferTypeResponse {
    fn from(result: InferTypeResponse) -> Self {
        let response = match result {
            InferTypeResponse::Success { value, type_scheme } => {
                ps::infer_type_response::Response::Success(ps::InferTypeSuccess {
                    type_scheme: Some(type_scheme.into()),
                    value: Some(value.into()),
                })
            }
            InferTypeResponse::Error { error } => {
                ps::infer_type_response::Response::Error(error.into())
            }
        };

        ps::InferTypeResponse {
            response: Some(response),
        }
    }
}

#[derive(Clone, Debug)]
/// A connection point that can be given to an external actor (worker/runtime).
pub struct Callback {
    /// Uri (i.e. hostname+port) to which to connect
    pub uri: Uri,
    /// The proverbial "void *extra" that allows the server at [Self::uri]
    /// to identify the caller (to whom this Callback was given) and tailor
    /// services as appropriate. (Typically, because the runtime at `uri`
    /// is acting on behalf of *another* runtime further up the tree, and
    /// the caller's requests should be forwarded back up the tree.)
    pub loc: Location,
}

impl TryFrom<pr::Callback> for Callback {
    type Error = ConvertError;

    fn try_from(value: pr::Callback) -> Result<Self, Self::Error> {
        let uri = value.uri.parse()?;
        let loc = TryInto::try_into(value.loc.ok_or(ConvertError::ProtoError)?)?;
        Ok(Callback { uri, loc })
    }
}

impl From<Callback> for pr::Callback {
    fn from(value: Callback) -> Self {
        pr::Callback {
            uri: value.uri.to_string(),
            loc: Some(value.loc.into()),
        }
    }
}

/// Crate version of [pw::RunFunctionRequest]
#[derive(Debug, Clone)]
#[allow(missing_docs)]
pub struct RunFunctionRequest {
    pub function: FunctionName,
    pub inputs: HashMap<Label, Value>,
    pub loc: Location,
    pub callback: Callback,
    metadata_map: MetadataMap,
}

impl RunFunctionRequest {
    /// Create a new instance given values for all fields except metadata
    /// (which will be empty)
    pub fn new(
        function: FunctionName,
        inputs: HashMap<Label, Value>,
        loc: Location,
        callback: Callback,
    ) -> Self {
        Self {
            function,
            inputs,
            loc,
            callback,
            metadata_map: Default::default(),
        }
    }

    /// Stores as metadata the trace to the graph node causing this request
    pub fn set_node_trace(&mut self, node_trace: NodeTrace) {
        self.metadata_map.append_bin(
            stack_trace_key(),
            MetadataValue::from_bytes(&node_trace.into_bytes()),
        );
    }

    /// Gets the trace of the graph node causing this request, if known
    pub fn get_node_trace(&self) -> Option<NodeTrace> {
        self.metadata_map
            .get_bin(stack_trace_key())
            .and_then(|md_trace| match parse_stack(md_trace) {
                Ok(tr) => Some(tr),
                Err(e) => {
                    tracing::warn!("Error parsing stack-trace in metadata: {e}");
                    None
                }
            })
    }

    /// Stores as metadata the job Uuid for this request
    pub fn set_job_id(&mut self, job_id: Uuid) {
        self.metadata_map
            .append_bin(job_id_key(), MetadataValue::from_bytes(job_id.as_bytes()));
    }

    /// Gets the job Uuid, if specified in the metadata
    pub fn get_job_id(&self) -> Option<Uuid> {
        self.metadata_map
            .get_bin(job_id_key())
            .and_then(|md_job_id| match parse_job_id(md_job_id) {
                Ok(job_id) => Some(job_id),
                Err(e) => {
                    tracing::warn!("Error parsing job-id in metadata: {e}");
                    None
                }
            })
    }
}

fn stack_trace_key() -> MetadataKey<Binary> {
    MetadataKey::from_static("tierkreis-stack-trace-bin")
}

fn parse_stack(md_trace: &MetadataValue<Binary>) -> Result<NodeTrace, Box<dyn std::error::Error>> {
    Ok(TryInto::try_into(pc::NodeId::decode(
        md_trace.to_bytes()?,
    )?)?)
}

fn job_id_key() -> MetadataKey<Binary> {
    MetadataKey::from_static("tierkreis-job-id-bin")
}

fn parse_job_id(md_job_id: &MetadataValue<Binary>) -> Result<Uuid, Box<dyn std::error::Error>> {
    Ok(Uuid::from_slice(&md_job_id.to_bytes()?)?)
}

impl TryFrom<tonic::Request<pw::RunFunctionRequest>> for RunFunctionRequest {
    type Error = ConvertError;

    fn try_from(req: tonic::Request<pw::RunFunctionRequest>) -> Result<Self, Self::Error> {
        let (metadata, _, value) = req.into_parts();
        Ok(RunFunctionRequest {
            function: TryInto::try_into(value.function.ok_or(ConvertError::ProtoError)?)?,
            inputs: TryInto::try_into(value.inputs.ok_or(ConvertError::ProtoError)?)?,
            loc: TryInto::try_into(value.loc.ok_or(ConvertError::ProtoError)?)?,
            callback: TryInto::try_into(value.callback.ok_or(ConvertError::ProtoError)?)?,
            metadata_map: metadata,
        })
    }
}

impl tonic::IntoRequest<pw::RunFunctionRequest> for RunFunctionRequest {
    fn into_request(self) -> tonic::Request<pw::RunFunctionRequest> {
        let mut req = pw::RunFunctionRequest {
            function: Some(self.function.into()),
            inputs: Some(self.inputs.into()),
            loc: Some(self.loc.into()),
            callback: Some(self.callback.into()),
        }
        .into_request();

        *req.metadata_mut() = self.metadata_map;
        req
    }
}

/// Crate version of [pw::RunFunctionResponse],
/// for when running a function was successful
#[derive(Debug, Clone)]
pub struct RunFunctionResponse {
    /// The function outputs
    pub outputs: HashMap<Label, Value>,
}

impl From<RunFunctionResponse> for pw::RunFunctionResponse {
    fn from(response: RunFunctionResponse) -> Self {
        pw::RunFunctionResponse {
            outputs: Some(response.outputs.into()),
        }
    }
}

/// Error to be reported from [Worker::run_function] as a GRPC error.
///
/// [Worker::run_function]: pw::worker_server::Worker::run_function
#[derive(Debug, Clone, Error)]
pub enum RunFunctionError {
    /// The requested function was not known
    #[error("unknown function: {0}")]
    UnknownFunction(FunctionName),
    /// Generic error in running the function
    #[error("runtime error: {0}")]
    RuntimeError(
        #[source]
        #[from]
        Arc<anyhow::Error>,
    ),
}

impl From<RunFunctionError> for tonic::Status {
    fn from(error: RunFunctionError) -> Self {
        match error {
            RunFunctionError::UnknownFunction(_) => tonic::Status::not_found(error.to_string()),
            RunFunctionError::RuntimeError(_) => tonic::Status::unknown(error.to_string()),
        }
    }
}

impl Reject for RunFunctionError {}

/// Crate version of [ps::ListFunctionsRequest]
#[derive(Debug, Clone)]
#[allow(missing_docs)]
pub struct ListFunctionsRequest {
    pub loc: Location,
}

impl TryFrom<ps::ListFunctionsRequest> for ListFunctionsRequest {
    type Error = ConvertError;

    fn try_from(value: ps::ListFunctionsRequest) -> Result<Self, Self::Error> {
        Ok(ListFunctionsRequest {
            loc: value
                .loc
                .map(TryInto::try_into)
                .transpose()?
                .unwrap_or_else(Location::local),
        })
    }
}

impl From<ListFunctionsRequest> for ps::ListFunctionsRequest {
    fn from(value: ListFunctionsRequest) -> Self {
        ps::ListFunctionsRequest {
            loc: Some(value.loc.into()),
        }
    }
}

impl tonic::IntoRequest<ps::ListFunctionsRequest> for ListFunctionsRequest {
    fn into_request(self) -> tonic::Request<ps::ListFunctionsRequest> {
        let x: ps::ListFunctionsRequest = self.into();
        x.into_request()
    }
}

/// Crate version of [pr::RunGraphRequest]
#[allow(missing_docs)]
pub struct RunGraphRequest {
    pub graph: Graph,
    pub inputs: HashMap<Label, Value>,
    pub type_check: bool,
    pub loc: Location,
    pub escape: Option<Callback>,
}

impl TryFrom<pr::RunGraphRequest> for RunGraphRequest {
    type Error = ConvertError;

    fn try_from(value: pr::RunGraphRequest) -> Result<Self, Self::Error> {
        Ok(RunGraphRequest {
            graph: TryInto::try_into(value.graph.ok_or(ConvertError::ProtoError)?)?,
            inputs: TryInto::try_into(value.inputs.ok_or(ConvertError::ProtoError)?)?,
            type_check: value.type_check,
            loc: TryInto::try_into(value.loc.ok_or(ConvertError::ProtoError)?)?,
            escape: value.escape.map(TryInto::try_into).transpose()?,
        })
    }
}

impl From<RunGraphRequest> for pr::RunGraphRequest {
    fn from(req: RunGraphRequest) -> Self {
        pr::RunGraphRequest {
            graph: Some(req.graph.into()),
            inputs: Some(req.inputs.into()),
            type_check: req.type_check,
            loc: Some(req.loc.into()),
            escape: req.escape.map(Into::into),
        }
    }
}

impl tonic::IntoRequest<pr::RunGraphRequest> for RunGraphRequest {
    fn into_request(self) -> tonic::Request<pr::RunGraphRequest> {
        let x: pr::RunGraphRequest = self.into();
        x.into_request()
    }
}

/// Crate version of [pr::RunGraphResponse]
#[derive(Debug, Clone)]
#[allow(missing_docs)]
pub enum RunGraphResponse {
    Success(HashMap<Label, Value>),
    TypeError(TypeErrors),
    Error(Arc<anyhow::Error>),
}

impl From<RunGraphResponse> for pr::RunGraphResponse {
    fn from(resp: RunGraphResponse) -> Self {
        let inner: pr::run_graph_response::Result = match resp {
            RunGraphResponse::Success(m) => pr::run_graph_response::Result::Success(m.into()),
            RunGraphResponse::TypeError(errors) => {
                pr::run_graph_response::Result::TypeErrors(errors.into())
            }
            RunGraphResponse::Error(err) => {
                pr::run_graph_response::Result::Error(format!("{:?}", err))
            }
        };

        pr::RunGraphResponse {
            result: Some(inner),
        }
    }
}

impl TryFrom<pr::RunGraphResponse> for RunGraphResponse {
    type Error = ConvertError;

    fn try_from(value: pr::RunGraphResponse) -> Result<Self, ConvertError> {
        match value.result.ok_or(ConvertError::ProtoError)? {
            pr::run_graph_response::Result::Success(x) => {
                Ok(RunGraphResponse::Success(TryInto::try_into(x)?))
            }
            pr::run_graph_response::Result::TypeErrors(_) => {
                Err(ConvertError::UnexpectedTypeErrors)
            }
            pr::run_graph_response::Result::Error(e) => {
                Ok(RunGraphResponse::Error(Arc::new(anyhow!(e))))
            }
        }
    }
}

#[cfg(test)]
mod test {
    use super::*;
    #[test]
    fn stack_trace_key_valid() {
        // MetadataKey::from_static panics if the key is not valid
        stack_trace_key();
    }
}
