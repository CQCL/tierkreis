use std::collections::HashMap;

use tierkreis_core::graph::Value;

use tierkreis_core::symbol::Label;

use tierkreis_proto::messages::{JobHandle, Message, NodeTrace};
use tierkreis_proto::protos_gen::v1alpha1::controller as pc;
use tierkreis_proto::protos_gen::v1alpha1::graph as pg;

type SystemServiceClient =
    pc::checkpoint_recording_service_client::CheckpointRecordingServiceClient<
        tonic::transport::Channel,
    >;

/// Allows reporting of checkpoint information for a specific job to a checkpointing server.
#[derive(Clone)]
pub struct CheckpointClient {
    /// Identifies the specific run of a graph (job uuid and attempt id)
    pub job_handle: JobHandle,
    client: SystemServiceClient,
}

impl CheckpointClient {
    /// Creates an instance for the specified job by connecting to a hostname and port
    pub async fn new(job_handle: JobHandle, host: &str, port: u16) -> anyhow::Result<Self> {
        let uri = format!("http://{}:{}", host, port);
        let client = SystemServiceClient::connect(uri).await?;
        Ok(Self { job_handle, client })
    }

    fn log_error(&self, message: &str, status: &tonic::Status) {
        let (job_uuid, attempt) = self.job_handle.into_inner();

        tracing::error!(
            tierkreis.job = job_uuid.to_string(),
            tierkreis.attempt = attempt,
            request = message,
            error = status.to_string(),
            "Failed to report to checkpoint store.",
        );
    }

    pub(super) async fn node_finished(
        &mut self,
        node_trace: NodeTrace,
        outputs: HashMap<Label, Value>,
    ) {
        let outputs: pg::StructValue = outputs.into();
        let (job_uuid, attempt) = self.job_handle.into_inner();

        let request = tonic::Request::new(pc::RecordNodeFinishedRequest {
            id: Some(node_trace.clone().into()),
            outputs: outputs.encode_to_vec(),
            job_id: job_uuid.to_string(),
            attempt_id: attempt,
        });

        if let Err(s) = self.client.record_node_finished(request).await {
            self.log_error(&format!("node {} finished.", node_trace), &s);
        }
    }

    pub(super) async fn node_started(
        &mut self,
        node_trace: NodeTrace,
        retry_after_secs: Option<u32>,
    ) {
        let (job_uuid, attempt) = self.job_handle.into_inner();
        let request = tonic::Request::new(pc::RecordNodeRunRequest {
            id: Some(node_trace.clone().into()),
            job_id: job_uuid.to_string(),
            expected_duration_sec: retry_after_secs,
            attempt_id: attempt,
        });

        if let Err(s) = self.client.record_node_run(request).await {
            self.log_error(&format!("node {} started.", node_trace), &s);
        }
    }

    pub(super) async fn job_finished(&mut self, error_message: Option<String>) {
        let (job_uuid, _) = self.job_handle.into_inner();
        let request = tonic::Request::new(pc::RecordJobFinishedRequest {
            job_id: job_uuid.to_string(),
            error_message,
        });

        if let Err(s) = self.client.record_job_finished(request).await {
            self.log_error("job finished.", &s);
        }
    }

    pub(super) async fn record_graph_output(&mut self, port: Label, value: Value) {
        let value = pg::Value::from(value);
        let (job_uuid, _) = self.job_handle.into_inner();

        let request = tonic::Request::new(pc::RecordOutputRequest {
            job_id: job_uuid.to_string(),
            label: port.to_string(),
            value: value.encode_to_vec(),
        });

        if let Err(s) = self.client.record_output(request).await {
            self.log_error(&format!("output {} recorded.", port), &s);
        }
    }
}
