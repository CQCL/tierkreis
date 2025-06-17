import logging
from pathlib import Path
from kubernetes import config, client  # type: ignore

config.load_config()  # type: ignore
# config.load_kube_config("~/.kube/config", "docker-desktop")  # type: ignore
crd_api = client.CustomObjectsApi()
api_client = crd_api.api_client  # type: ignore
logger = logging.getLogger(__name__)


def generate_job_crd(job_name: str, image: str, worker_call_args_path: Path):
    metadata = client.V1ObjectMeta(
        generate_name=job_name, labels={"kueue.x-k8s.io/queue-name": "tierkreis-queue"}
    )
    pv_name = "tierkreis-pv-storage"
    volume = client.V1Volume(
        name=pv_name,
        host_path=client.V1HostPathVolumeSource(path=str(Path.home() / ".tierkreis")),
    )
    volume_mount = client.V1VolumeMount(
        mount_path=str(Path.home() / ".tierkreis"), name=pv_name
    )
    container = client.V1Container(
        image=image,
        name="tierkreis-job",
        command=[
            "python",
            "/tierkreis/tierkreis/controller/builtins/main.py",
            str(worker_call_args_path),
        ],
        image_pull_policy="IfNotPresent",
        volume_mounts=[volume_mount],
        resources=client.V1ResourceRequirements(
            limits={"cpu": "0.2", "memory": "100M"}
        ),
    )
    template = client.V1PodTemplateSpec(
        spec=client.V1PodSpec(
            containers=[container], restart_policy="Never", volumes=[volume]
        )
    )
    return client.V1Job(
        api_version="batch/v1",
        kind="Job",
        metadata=metadata,
        spec=client.V1JobSpec(suspend=True, template=template, backoff_limit=3),
    )


class KueueExecutor:
    disable_builtins: bool = True

    def __init__(self, logs_path: Path) -> None:
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
        crd = generate_job_crd(
            f"tkr-{launcher_name}", f"tkr_{launcher_name}", node_definition_path
        )
        batch_api.create_namespaced_job("tierkreis-kueue", crd)  # type: ignore
