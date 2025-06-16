import logging
from pathlib import Path
from typing import Any
from kubernetes import config, client  # type: ignore

config.load_kube_config("~/.kube/config", "docker-desktop")  # type: ignore
crd_api = client.CustomObjectsApi()
api_client = crd_api.api_client  # type: ignore


logger = logging.getLogger(__name__)


def generate_job_crd(job_name: str, image: str, worker_call_args_path: Path):
    """
    Generate an equivalent job CRD to sample-job.yaml
    """
    metadata = client.V1ObjectMeta(
        generate_name=job_name, labels={"kueue.x-k8s.io/queue-name": "tierkreis-queue"}
    )

    # Job container
    container = client.V1Container(
        image=image,
        name="testjob",
        args=[str(worker_call_args_path)],
        # resources={"requests": {"cpu": 0.2, "memory": "200Mi"}},
        image_pull_policy="IfNotPresent",
    )

    # Job template
    template: dict[str, Any] = {
        "spec": {"containers": [container], "restartPolicy": "Never"}
    }
    return client.V1Job(
        api_version="batch/v1",
        kind="Job",
        metadata=metadata,
        spec=client.V1JobSpec(suspend=True, template=template, backoff_limit=3),
    )


class KueueExecutor:
    def __init__(self, registry_path: Path, logs_path: Path) -> None:
        self.launchers_path = registry_path
        self.logs_path = logs_path
        self.errors_path = logs_path

    def run(self, launcher_name: str, node_definition_path: Path) -> None:
        logging.basicConfig(
            format="%(asctime)s: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
            filename=self.logs_path,
            filemode="a",
            level=logging.INFO,
        )
        self.errors_path = node_definition_path.parent / "errors"
        logger.info("START %s %s", launcher_name, node_definition_path)

        batch_api = client.BatchV1Api()
        crd = generate_job_crd("testjobname", "tkr_builtins:4", node_definition_path)

        batch_api.create_namespaced_job("tierkreis-kueue", crd)  # type: ignore
