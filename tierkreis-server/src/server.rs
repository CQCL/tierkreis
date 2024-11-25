//! Handles multiple/concurrent requests but abstracted from the transport
//! mechanism (e.g. GRPC) via which said requests may be made.
use anyhow::anyhow;
use dashmap::mapref::entry::Entry;
use dashmap::mapref::one::Ref;
use dashmap::DashMap;
use http::Uri;
use std::collections::HashMap;
use std::sync::Arc;
use tierkreis_core::symbol::{Location, LocationName};
use tierkreis_runtime::operations::CheckpointClient;
use tierkreis_runtime::workers::{
    CallbackForwarder, ClientInterceptor, EscapeHatch, FunctionForwarder,
};
use tierkreis_runtime::Runtime;
use tierkreis_runtime::{operations::TaskHandle, RunGraphError};
use tokio::sync::RwLock;
use tracing::instrument;

use tierkreis_proto::messages::{
    Callback, DeleteCompletedResponse, InferTypeRequest, JobHandle, JobInfo, JobStatusError,
    JobStatusRequest, JobStatusResponse, ListFunctionsRequest, RunFunctionError,
    RunFunctionRequest, RunFunctionResponse, RunGraphRequest, RunGraphResponse, RunningJobsRequest,
    RunningJobsResponse, StartJobRequest, StartJobResponse, Status, StopJobRequest,
    StopJobResponse, UnknownJob,
};
use tierkreis_proto::protos_gen::v1alpha1::signature as ps;
use uuid::Uuid;

/// State and data for a server.
/// The same TierkreisServer can handle both
/// [TierkreisServer::run_graph] requests (which have callbacks and escape hatches),
/// and [TierkreisServer::start_job] requests (with asynchronous job management).
#[derive(Clone)]
pub struct TierkreisServer {
    runtime: Runtime,
    // Forwarding for callbacks (from workers executing run_function),
    // of run_graph and other calls (except run_function).
    cb_forwarding: Arc<DashMap<LocationName, CallbackForwarder>>,
    // Forwarding for escape hatches (from child runtimes executing run_graph),
    // of run_function calls only.
    eh_forwarding: Arc<DashMap<LocationName, FunctionForwarder>>,
    interceptor: ClientInterceptor,
    callback_uri: Uri,
    state: Arc<RwLock<State>>,
    checkpoint_endpoint: Option<(String, u16)>,
}

struct State {
    tasks: HashMap<JobHandle, TaskHandle>,
}

impl TierkreisServer {
    /// Create a new instance.
    /// `callback_uri` is the Uri to pass to workers which may use it to execute
    /// [Self::run_graph] callbacks - i.e. the Uri of this server if no other.
    /// If `checkpoint_endpoint` is not None, it is a (hostname, port) to which
    /// checkpoints will be reported for graphs run via [Self::start_job]
    pub fn new(
        runtime: Runtime,
        interceptor: ClientInterceptor,
        callback_uri: Uri,
        checkpoint_endpoint: Option<(String, u16)>,
    ) -> Self {
        Self {
            runtime,
            cb_forwarding: Arc::new(DashMap::new()),
            eh_forwarding: Arc::new(DashMap::new()),
            interceptor,
            callback_uri,
            state: Arc::new(RwLock::new(State::new())),
            checkpoint_endpoint,
        }
    }
}

impl std::fmt::Debug for TierkreisServer {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("TierkreisServer").finish()
    }
}

impl State {
    pub fn new() -> Self {
        Self {
            tasks: HashMap::new(),
        }
    }
}

impl Default for State {
    fn default() -> Self {
        Self::new()
    }
}

impl TierkreisServer {
    fn should_forward_cb(
        &self,
        loc: &Location,
    ) -> Option<(Ref<'_, LocationName, CallbackForwarder>, Location)> {
        loc.clone()
            .pop()
            .and_then(|(hd, tl)| self.cb_forwarding.get(&hd).map(|r| (r, tl)))
    }

    fn should_fwd_run_func(
        &self,
        loc: &Location,
    ) -> Option<(Ref<'_, LocationName, FunctionForwarder>, Location)> {
        loc.clone()
            .pop()
            .and_then(|(hd, tl)| self.eh_forwarding.get(&hd).map(|r| (r, tl)))
    }

    /// Lists all jobs started by [Self::start_job] that
    /// have not been removed by [Self::delete_completed]
    #[instrument(skip(_request, self))]
    pub async fn running_jobs(&self, _request: RunningJobsRequest) -> RunningJobsResponse {
        let jobs = self
            .state
            .read()
            .await
            .tasks
            .iter()
            .map(|(id, handle)| {
                let status = handle.status();
                JobInfo {
                    handle: *id,
                    status,
                }
            })
            .collect();
        RunningJobsResponse { jobs }
    }

    /// Gets the status of a job started via [Self::start_job]
    #[instrument(skip(request, self))]
    pub async fn job_status(
        &self,
        request: JobStatusRequest,
    ) -> Result<JobStatusResponse, JobStatusError> {
        let handle = self
            .state
            .read()
            .await
            .tasks
            .get(&request.handle)
            .ok_or(JobStatusError::UnknownTask(request.handle))?
            .clone();
        Ok(JobStatusResponse {
            job_info: JobInfo {
                handle: request.handle,
                status: handle.status(),
            },
        })
    }

    /// Starts a new job running a graph, returning either the job handle
    /// passed in, or an error if such occurred before starting to evaluate the graph
    /// (e.g. if a job with that handle already existed, or the graph failed to typecheck).
    #[instrument(name = "Start job", skip(request, self), fields(_job_handle = request.job_handle.to_string()))]
    pub async fn start_job(&self, request: StartJobRequest) -> StartJobResponse {
        let callback = Callback {
            uri: self.callback_uri.clone(),
            loc: Location::local(),
        };

        let checkpoint_config = if let Some((host, port)) = &self.checkpoint_endpoint {
            let Ok(client) = CheckpointClient::new(request.job_handle, host, *port).await else {
                return StartJobResponse::RuntimeError(
                    "Checkpoint endpoint connection failed".to_string(),
                );
            };
            Some(client)
        } else {
            None
        };

        let result = self.runtime.start_graph(
            request.graph,
            request.inputs,
            true,
            callback.clone(),
            EscapeHatch::this_runtime(callback),
            checkpoint_config,
        );

        let handle = match result {
            Ok(handle) => {
                tracing::info!(
                    job_id = request.job_handle.to_string(),
                    "type check succeeded"
                );
                handle
            }
            Err(error) => {
                tracing::warn!(job_id = request.job_handle.to_string(), "type check failed");
                return StartJobResponse::TypeErrors(error);
            }
        };

        if self
            .state
            .write()
            .await
            .tasks
            .insert(request.job_handle, handle)
            .is_some()
        {
            return StartJobResponse::RuntimeError(format!("Job ID clash {}", request.job_handle));
        }

        tracing::info!(job_id = request.job_handle.to_string(), "Job started.");
        StartJobResponse::JobId(request.job_handle)
    }

    /// Stops a job started by [Self::start_job] given the [JobHandle::job_uuid]
    #[instrument(skip(request, self))]
    pub async fn stop_job(&self, request: StopJobRequest) -> Result<StopJobResponse, UnknownJob> {
        // TODO can use nested hashmap to avoid O(n) search
        let job_handles_to_cancel: Vec<JobHandle> = self
            .state
            .read()
            .await
            .tasks
            .keys()
            .filter(|job_handle| job_handle.job_uuid() == &request.job_id)
            .cloned()
            .collect();
        if job_handles_to_cancel.is_empty() {
            return Err(UnknownJob(request.job_id));
        }
        if job_handles_to_cancel.len() > 1 {
            tracing::warn!("Multiple attempts of same job, all will be stopped.");
        }

        for job_handle in job_handles_to_cancel {
            let handle = self.state.write().await.tasks.remove(&job_handle).unwrap();
            handle.cancel();
        }
        Ok(StopJobResponse)
    }

    /// Clears out all [Status::Completed] jobs started by [Self::start_job]
    /// such that they are no longer listed by [Self::running_jobs]
    #[instrument(skip(self))]
    pub async fn delete_completed(&self) -> DeleteCompletedResponse {
        let to_delete: Vec<JobHandle> = self
            .state
            .read()
            .await
            .tasks
            .iter()
            .filter_map(|(id, handle)| {
                if let Status::Completed(_) = handle.status() {
                    Some(*id)
                } else {
                    None
                }
            })
            .collect();
        for handle in to_delete.iter() {
            self.stop_job(StopJobRequest {
                job_id: *handle.job_uuid(),
            })
            .await
            .expect("job known to exist");
        }
        DeleteCompletedResponse {
            deleted_jobs: to_delete,
        }
    }

    /// Runs type inference on a graph, returning the same graph but with type annotations
    #[instrument(skip(request, self))]
    pub async fn infer_type(
        &self,
        request: InferTypeRequest,
    ) -> anyhow::Result<ps::InferTypeResponse> {
        if let Some((w, loc)) = self.should_forward_cb(&request.loc) {
            (*w).as_runtime_worker()
                .infer_type(request.value, loc)
                .await
        } else {
            self.runtime
                .infer_type_in_loc(request.value, request.loc)
                .await
        }
    }

    /// Runs a function (e.g. a builtin, or on a worker).
    /// Returns the function results as a `HashMap<String, [TierkreisValue]`, or an error.
    #[instrument(skip(request, self))]
    pub async fn run_function(
        &self,
        request: RunFunctionRequest,
    ) -> Result<RunFunctionResponse, RunFunctionError> {
        let outputs = if let Some((c, loc)) = self.should_fwd_run_func(&request.loc) {
            let node_trace = request.get_node_trace();
            (*c).fwd_run_function(
                request.function,
                request.inputs,
                loc,
                request.callback,
                node_trace,
            )
            .await
            .map_err(|e| RunFunctionError::RuntimeError(Arc::new(e)))?
        } else {
            let parent =
                CallbackForwarder::new_connect(&request.callback.uri, self.interceptor.clone())
                    .await
                    .map_err(Arc::new)?;

            let ln = LocationName::from_uuid(Uuid::new_v4());

            match self.cb_forwarding.entry(ln) {
                Entry::Occupied(_) => {
                    return Err(RunFunctionError::RuntimeError(
                        // This *really* shouldn't happen; perhaps we should just panic?
                        Arc::new(anyhow!("Guid clash {}", ln)),
                    ));
                }
                Entry::Vacant(v) => v.insert(parent),
            };

            let graph_trace = request.get_node_trace().map(Into::into).unwrap_or_default();
            let operation = self
                .runtime
                .run_function_with_loc(&request.function, &request.loc)
                .ok_or(RunFunctionError::UnknownFunction(request.function))?;

            let callback = Callback {
                uri: self.callback_uri.clone(),
                // We require the client to pass back the entire chain of callback UUIDs.
                // The prepended element identifies the parent onto whom to forward the rest.
                loc: request.callback.loc.clone().prepend(ln),
            };

            // run_function (worker) calls should never need an escape hatch
            // (that is, for now, we assume that a worker should not be told the escape hatch
            // so that it can pass it as parameter when making a callback.)
            // However, the OperationContext requires we supply one.
            let escape = EscapeHatch::this_runtime(Callback {
                uri: self.callback_uri.clone(),
                // We don't add `ln` to the `eh_forwarding` map so this should never match.
                // (A fresh UUID would be more defensive still, but seems wasteful of UUIDs.)
                loc: Location::local().prepend(ln),
            });

            let outputs = operation
                .run_simple(
                    self.runtime.clone(),
                    callback,
                    escape,
                    request.inputs,
                    graph_trace,
                    None,
                )
                .into_task()
                .complete()
                .await?;
            self.cb_forwarding.remove(&ln);

            outputs.as_ref().clone()
        };
        Ok(RunFunctionResponse { outputs })
    }

    /// Runs a graph, returning a `HashMap<String, [TierkreisValue]>` of the graph
    /// results, or an error (e.g. typecheck failure)
    #[instrument(skip(request, self))]
    pub async fn run_graph(&self, request: RunGraphRequest) -> RunGraphResponse {
        let RunGraphRequest {
            graph,
            inputs,
            type_check,
            loc,
            escape,
        } = request;
        let res = if let Some((w, rest)) = self.should_forward_cb(&loc) {
            // Forwarding a run_graph back up the tree to the closest enclosing scope.
            // Such requests come from workers, and we do not give escape hatches to workers.
            assert!(escape.is_none()); // If it happens, we need to decide what to do.
                                       // Either leave intact, or if the escape hatch is a forwarding chain back up the tree,
                                       // we should unwrap it by one level.
            (*w).as_runtime_worker()
                .execute_graph(graph, inputs, rest, type_check, escape)
                .await
        } else {
            // RunGraphRequest does not contain a callback, as any callback should
            // only come back up the tree of runtimes as far as the first run_graph
            let callback = Callback {
                uri: self.callback_uri.clone(),
                loc: Location::local(),
            };
            // However, it may contain an escape - if so, connect, and set up forwarding
            let forward = match escape {
                None => None,
                Some(parent) => {
                    let ff = match FunctionForwarder::new(
                        &parent.uri,
                        self.interceptor.clone(),
                        parent.loc,
                    )
                    .await
                    {
                        Ok(f) => f,
                        Err(e) => return RunGraphResponse::Error(Arc::new(e)),
                    };
                    // Note we could ask the Connection for a signature here, and add
                    // those functions to the local runtime (cloning+mutating). Such would
                    // make the "escape hatch" behave more like a conventional extra worker,
                    // and allow typechecking. However, instead we use a "fire-and-hope" approach.
                    let ln = LocationName::from_uuid(Uuid::new_v4());
                    if self.eh_forwarding.insert(ln, ff.clone()).is_some() {
                        // Perhaps we should just panic here
                        return RunGraphResponse::Error(Arc::new(anyhow!("UUID clash {}", ln)));
                    }
                    Some((ln, ff))
                }
            };
            let key = forward.as_ref().map(|(ln, _)| *ln);
            let escape_proxy = Callback {
                uri: self.callback_uri.clone(),
                loc: Location(key.into_iter().collect()),
            };
            let res = match loc.pop() {
                Some(remote_loc) => {
                    self.runtime
                        .execute_graph_remote(graph, inputs, type_check, remote_loc, escape_proxy)
                        .await
                }
                None => {
                    let escape = EscapeHatch::new(forward.map(|(_, ff)| ff), escape_proxy);
                    self.runtime
                        .execute_graph_cb(graph, inputs, type_check, callback, escape)
                        .await
                }
            };
            key.map(|k| self.eh_forwarding.remove(&k));
            res
        };

        match res {
            Ok(outputs) => RunGraphResponse::Success(outputs),
            Err(RunGraphError::TypeError(e)) => RunGraphResponse::TypeError(e),
            Err(RunGraphError::RuntimeError(e)) => RunGraphResponse::Error(e),
        }
    }

    /// List all functions known/available to this server, i.e., get the signature
    #[instrument(skip(request, self))]
    pub async fn list_functions(
        &self,
        request: ListFunctionsRequest,
    ) -> anyhow::Result<ps::ListFunctionsResponse> {
        if let Some((w, loc)) = self.should_forward_cb(&request.loc) {
            (*w).signature(loc).await
        } else {
            self.runtime.signature_in_loc(request.loc).await
        }
    }
}
