"""Worker server implementation."""

import sys
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Coroutine, Optional, cast

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
import keyring

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
            with span as s:
                from .prelude import profile_worker  # avoid cyclic import

                if profile_worker:
                    import cProfile, pstats  # could be global
                    from io import StringIO

                    render_results = StringIO()
                    with cProfile.Profile() as pr:
                        # If there are multiple requests being processed at the
                        # same time, due to "async" this will likely get confused,
                        # i.e. combine processing for any+all of them together.
                        pr.enable()
                        await method_func(stream)
                        pr.disable()
                        stats = pstats.Stats(pr, stream=render_results)
                    stats.sort_stats("cumtime")
                    stats.print_stats(20)  # Top 20 lines
                    render_results.seek(0)
                    s.set_attribute("profile_results", render_results.read())
                else:
                    await method_func(stream)

        finally:
            opentelemetry.context.detach(token)

    request.method_func = wrapped


_KEYRING_SERVICE = "tierkreis_extracted"


class Worker:
    """Worker server."""

    functions: dict[str, Function]
    aliases: dict[str, TypeScheme]
    server: Server
    callback: Optional[tuple[str, int]] = None

    def __init__(self):
        self.functions = {}
        self.aliases = {}
        self.server = Server([SignatureServerImpl(self), WorkerServerImpl(self)])

        # Attach event listener for tracing
        self._add_request_listener(_event_recv_request)
        # Attach event listener to pick up callback address
        self._add_request_listener(self._extract_callback)
        # Attach event listener to extract auth credentials
        self._add_request_listener(self._extract_auth)

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

    async def _extract_callback(self, request: grpclib.events.RecvRequest):
        if self.callback is None:
            callback_host = str(request.metadata.get("tierkreis_callback_host"))
            callback_port = int(request.metadata.get("tierkreis_callback_port"))  # type: ignore

            self.callback = (callback_host, callback_port)

    async def _extract_auth(self, request: grpclib.events.RecvRequest) -> None:
        if keyring.get_password(_KEYRING_SERVICE, "token") is None:
            token = request.metadata.pop("token", None)
            key = request.metadata.pop("key", None)
            if (token is not None) and (key is not None):
                keyring.set_password(_KEYRING_SERVICE, "token", str(token))
                keyring.set_password(_KEYRING_SERVICE, "key", str(key))

    def _add_request_listener(
        self,
        listener: Callable[[grpclib.events.RecvRequest], Coroutine[Any, Any, None]],
    ):
        grpclib.events.listen(self.server, grpclib.events.RecvRequest, listener)

    async def start(self, port: Optional[int] = None):
        """Start server."""

        if port:
            await self.server.start(port=port)

            print(f"Started worker server on port: {port}", flush=True)
            await self.server.wait_closed()

        else:
            with TemporaryDirectory() as socket_dir:
                # Create a temporary path for a unix domain socket.
                socket_path = f"{socket_dir}/python_worker.sock"

                # Start the python worker gRPC server and bind to the unix domain socket
                await self.server.start(path=socket_path)

                # Print the path of the unix domain socket to stdout so the runtime can
                # connect to it. Without the flush the runtime did not receive the
                # socket path and blocked indefinitely.
                print(socket_path)
                sys.stdout.flush()

                await self.server.wait_closed()

        # clear any stored credentials
        keyring.delete_password(_KEYRING_SERVICE, "token")
        keyring.delete_password(_KEYRING_SERVICE, "key")


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
            with tracer.start_as_current_span(
                "encoding python type in RunFunctionResponse proto"
            ):
                res = RunFunctionResponse(
                    outputs=pg.StructValue(outputs_struct.to_proto_dict())
                )
            return res
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
