"""Prelude definitions and functions for server executable scripts."""

import argparse
import asyncio
import os

import opentelemetry.trace  # type: ignore
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (  # type: ignore
    OTLPSpanExporter,
)
from opentelemetry.sdk.resources import SERVICE_NAME, Resource  # type: ignore
from opentelemetry.sdk.trace import TracerProvider  # type: ignore
from opentelemetry.sdk.trace.export import SimpleSpanProcessor  # type: ignore

from .namespace import Namespace
from .worker import Worker

parser = argparse.ArgumentParser(description="Parse worker server cli.")
parser.add_argument(
    "--port", help="If specified listen on network port rather than UDP."
)


def setup_tracing(service_name: str):

    endpoint = os.environ.get("TIERKREIS_OTLP")

    if endpoint is None:
        return

    tracer_provider = TracerProvider(
        resource=Resource.create({SERVICE_NAME: service_name})
    )

    span_exporter = OTLPSpanExporter(endpoint=endpoint)

    tracer_provider.add_span_processor(SimpleSpanProcessor(span_exporter))

    opentelemetry.trace.set_tracer_provider(tracer_provider)


def start_worker_server(worker: Worker, worker_name: str, namespaces=list[Namespace]):
    """Set up tracing and run the worker server with the provided namespaces.
    Expects a port specified on the command line, and reports succesful start to
    stdout"""

    async def main():
        args = parser.parse_args()
        setup_tracing(worker_name)
        for namespace in namespaces:
            worker.add_namespace(namespace)
        await worker.start(args.port)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
