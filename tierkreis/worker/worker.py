"""Worker server implementation."""

import sys
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, Any, Awaitable, Optional, cast

import grpclib
import grpclib.events
import grpclib.server
import opentelemetry.context  # type: ignore
import opentelemetry.propagate  # type: ignore
import opentelemetry.trace  # type: ignore
from grpclib.const import Status as StatusCode
from grpclib.exceptions import GRPCError
from grpclib.server import Server
from opentelemetry.semconv.trace import SpanAttributes  # type: ignore
import tierkreis.core.protos.tierkreis.graph as pg
import tierkreis.core.protos.tierkreis.signature as ps
from tierkreis.core.protos.tierkreis.worker import RunFunctionResponse, WorkerBase
from tierkreis.core.types import TypeScheme
from tierkreis.core.values import StructValue

from .exceptions import (
    DecodeInputError,
    EncodeOutputError,
    FunctionNotFound,
    NodeExecutionError,
)
from .namespace import Function

if TYPE_CHECKING:
    from .namespace import Namespace

tracer = opentelemetry.trace.get_tracer(__name__)


async def _event_recv_request(request: grpclib.events.RecvRequest):
    method_func = request.method_func
    context = opentelemetry.propagate.extract(request.metadata)

    service, method = request.method_name.lstrip("/").split("/", 1)

    attributes = {
        SpanAttributes.RPC_SYSTEM: "grpc",
        SpanAttributes.RPC_SERVICE: service,
        SpanAttributes.RPC_METHOD: method,
    }

    async def wrapped(stream: grpclib.server.Stream):
        token = opentelemetry.context.attach(context)
        try:
            span = tracer.start_as_current_span(
                name=f"GRPC: {request.method_name}",
                kind=opentelemetry.trace.SpanKind.SERVER,
                attributes=attributes,
            )
            with span:
                await method_func(stream)
        finally:
            opentelemetry.context.detach(token)

    request.method_func = wrapped


class Worker:
    """Worker server."""

    functions: dict[str, Function]
    aliases: dict[str, TypeScheme]

    def __init__(self):
        self.functions = {}
        self.aliases = {}

    def add_namespace(self, namespace: "Namespace"):
        """Add namespace of functions to workspace."""
        for (name, function) in namespace.functions.items():
            newname = f"{namespace.name}/{name}"
            function.declaration.name = newname
            self.functions[newname] = function

        for (name, type_) in namespace.aliases.items():
            newname = f"{namespace.name}/{name}"
            self.aliases[newname] = type_

    def run(self, function: str, inputs: StructValue) -> Awaitable[StructValue]:
        """Run function."""
        if function not in self.functions:
            raise FunctionNotFound(function)

        func = self.functions[function]

        # See https://github.com/python/mypy/issues/5485
        return cast(Any, func).run(inputs)

    async def start(self, port: Optional[str] = None):
        """Start server."""
        server = Server([SignatureServerImpl(self), WorkerServerImpl(self)])

        # Attach event listener for tracing
        grpclib.events.listen(server, grpclib.events.RecvRequest, _event_recv_request)

        if port:
            await server.start(port=int(port))

            print(f"Started worker server on port: {port}", flush=True)
            await server.wait_closed()

        else:
            with TemporaryDirectory() as socket_dir:
                # Create a temporary path for a unix domain socket.
                socket_path = f"{socket_dir}/python_worker.sock"

                # Start the python worker gRPC server and bind to the unix domain socket
                await server.start(path=socket_path)

                # Print the path of the unix domain socket to stdout so the runtime can
                # connect to it. Without the flush the runtime did not receive the
                # socket path and blocked indefinitely.
                print(socket_path)
                sys.stdout.flush()

                await server.wait_closed()


class WorkerServerImpl(WorkerBase):
    worker: Worker

    def __init__(self, worker: Worker):
        self.worker = worker

    async def run_function(
        self, function: str, inputs: "pg.StructValue"
    ) -> "RunFunctionResponse":
        try:
            inputs_struct = StructValue.from_proto_dict(inputs.map)
            outputs_struct = await self.worker.run(function, inputs_struct)
            outputs = pg.StructValue(outputs_struct.to_proto_dict())
            return RunFunctionResponse(outputs=outputs)
        except DecodeInputError as err:
            raise GRPCError(
                status=StatusCode.INVALID_ARGUMENT,
                message=f"Error while decoding inputs: {err}",
            ) from err
        except EncodeOutputError as err:
            raise GRPCError(
                status=StatusCode.INTERNAL,
                message=f"Error while encoding outputs: {err}",
            ) from err
        except FunctionNotFound as err:
            raise GRPCError(
                status=StatusCode.UNIMPLEMENTED,
                message=f"Unsupported function: {function}",
            ) from err
        except NodeExecutionError as err:
            raise GRPCError(
                status=StatusCode.UNKNOWN,
                message=f"Error while running operation: {repr(err.base_exception)}",
            ) from err


class SignatureServerImpl(ps.SignatureBase):
    worker: Worker

    def __init__(self, worker: Worker):
        self.worker = worker

    async def list_functions(self) -> "ps.ListFunctionsResponse":
        functions = {
            function_name: function.declaration.to_proto()
            for (function_name, function) in self.worker.functions.items()
        }

        aliases = {
            alias_name: type_scheme.to_proto()
            for (alias_name, type_scheme) in self.worker.aliases.items()
        }

        return ps.ListFunctionsResponse(functions=functions, aliases=aliases)
