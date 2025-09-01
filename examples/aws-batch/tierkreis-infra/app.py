#!/usr/bin/env python3
from pathlib import Path
import aws_cdk as cdk

from aws_cdk import Stack, Size
from aws_cdk.aws_ecr_assets import Platform
from aws_cdk.aws_ec2 import Vpc, InstanceType
from aws_cdk.aws_ecs import ContainerImage
from aws_cdk.aws_batch import (
    ManagedEc2EcsComputeEnvironment,
    AllocationStrategy,
    JobQueue,
    EcsEc2ContainerDefinition,
    EcsJobDefinition,
)
from constructs import Construct

EXAMPLES_DIR = Path(__file__).parent.parent.parent


class TierkreisInfraStack(Stack):

    def __init__(self, scope: Construct, cid: str) -> None:
        super().__init__(scope, cid)

        vpc = Vpc(self, f"{cid}-vpc")
        env = ManagedEc2EcsComputeEnvironment(
            self,
            f"{cid}-env",
            vpc=vpc,
            instance_types=[InstanceType("default_x86_64")],
            allocation_strategy=AllocationStrategy.BEST_FIT_PROGRESSIVE,
            minv_cpus=0,
            maxv_cpus=12,
        )
        queue = JobQueue(self, f"{cid}-queue")
        queue.add_compute_environment(env, 1)

        container = EcsEc2ContainerDefinition(
            self,
            f"{cid}-hello-world-worker",
            image=ContainerImage.from_asset(
                f"{EXAMPLES_DIR}/example_workers/hello_world_worker",
                platform=Platform.LINUX_AMD64,
            ),
            memory=Size.mebibytes(256),
            cpu=1,
        )
        EcsJobDefinition(self, f"{cid}-test-job", container=container)


app = cdk.App()
TierkreisInfraStack(app, "tierkreis")
app.synth()
