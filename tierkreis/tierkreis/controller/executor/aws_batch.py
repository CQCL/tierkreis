import logging
from pathlib import Path
from time import time

import boto3
from mypy_boto3_batch import BatchClient

client: BatchClient = boto3.client("batch")
logger = logging.getLogger(__name__)


class AwsBatchExecutor:
    def run(self, launcher_name: str, worker_call_args_path: Path) -> None:
        logger.info("SUBMIT %s %s", launcher_name, worker_call_args_path)
        client.submit_job(
            jobName=f"{launcher_name}{time()}",
            jobQueue="tierkreis",
            jobDefinition=f"tkr_{launcher_name}",
            containerOverrides={"command": [str(worker_call_args_path)]},
        )
