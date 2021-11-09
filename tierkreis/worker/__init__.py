"""Tools to enable python Tierkreis workers."""

import argparse
import asyncio
import dataclasses
import os
import sys
import typing
from dataclasses import dataclass, make_dataclass
from functools import wraps
from inspect import getdoc, isclass
from tempfile import TemporaryDirectory
from typing import Any, Awaitable, Callable, Dict, List, Optional, Type, Union, cast

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
from tierkreis.core.function import TierkreisFunction
from tierkreis.core.protos.tierkreis.worker import RunFunctionResponse, WorkerBase
from tierkreis.core.tierkreis_struct import TierkreisStruct
from tierkreis.core.types import Constraint, GraphType, Kind, Row, StarKind, TypeScheme
from tierkreis.core.values import StructValue, TierkreisValue

tracer = opentelemetry.trace.get_tracer(__name__)


def _snake_to_pascal(name: str) -> str:
    return name.replace("_", " ").title().replace(" ", "")


@dataclass
class Function:
    """Registered python function."""

    run: Callable[[StructValue], Awaitable[StructValue]]
    declaration: TierkreisFunction


def _get_base_tkstruct(class_type: Type) -> Type:
    origin = typing.get_origin(class_type)
    return origin if origin is not None else class_type


def _get_ordered_names(struct: Type) -> List[str]:
    tk_cls = _get_base_tkstruct(struct)
    return [field.name for field in dataclasses.fields(tk_cls)]


# Convert the type vars to names
def _type_var_to_name(type_var: Union[str, typing.TypeVar]) -> str:
    if isinstance(type_var, typing.TypeVar):
        return type_var.__name__
    return type_var


def _check_tkstruct_hint(hint: Type) -> bool:
    tk_cls = _get_base_tkstruct(hint)
    return (
        tk_cls is not None and isclass(tk_cls) and issubclass(tk_cls, TierkreisStruct)
    )


class Namespace:
    """Namespace containing Tierkreis Functions"""

    name: str
    functions: Dict[str, Function]

    def __init__(self, name: str):
        self.name = name
        self.functions = {}

    def function(
        self,
        name: Optional[str] = None,
        constraints: Optional[List[Constraint]] = None,
        type_vars: Optional[Dict[Union[str, typing.TypeVar], Kind]] = None,
    ):
        """Decorator to mark python function as available Namespace."""

        def decorator(func):
            func_name = name or func.__name__

            # Get input and output type hints
            type_hints = typing.get_type_hints(func)

            if "return" not in type_hints:
                raise ValueError("Tierkreis function needs return type hint.")
            return_hint = type_hints.pop("return")

            struct_input = "inputs" in type_hints and _check_tkstruct_hint(
                type_hints["inputs"]
            )

            hint_inputs: Type = (
                type_hints["inputs"]
                if struct_input
                else make_dataclass(
                    f"{_snake_to_pascal(func_name)}Inputs", type_hints.items()
                )
            )

            struct_output = _check_tkstruct_hint(return_hint)
            hint_outputs: Type = (
                return_hint
                if struct_output
                else make_dataclass(
                    f"{_snake_to_pascal(func_name)}Outputs", [("value", return_hint)]
                )
            )

            # Convert type hints into tierkreis types
            type_inputs = Row.from_python(hint_inputs)
            type_outputs = Row.from_python(hint_outputs)

            # Wrap function with input and output conversions
            @wraps(func)
            async def wrapped_func(inputs: StructValue) -> StructValue:
                try:
                    with tracer.start_as_current_span("decoding inputs to python type"):
                        python_inputs = (
                            {"inputs": inputs.to_python(hint_inputs)}
                            if struct_input
                            else {
                                name: val.to_python(type_hints[name])
                                for name, val in inputs.values.items()
                            }
                        )
                except Exception as error:
                    raise DecodeInputError(str(error)) from error

                try:
                    python_outputs = await func(**python_inputs)
                except Exception as error:
                    raise NodeExecutionError(error) from error

                try:
                    with tracer.start_as_current_span(
                        "encoding outputs from python type"
                    ):
                        outputs = TierkreisValue.from_python(python_outputs)
                except Exception as error:
                    raise EncodeOutputError(str(error)) from error
                return (
                    cast(StructValue, outputs)
                    if struct_output
                    else StructValue({"value": outputs})
                )

            type_vars_by_name = (
                {_type_var_to_name(var): kind for var, kind in type_vars.items()}
                if type_vars
                else {}
            )

            type_vars_by_name.update(
                {name: StarKind() for name in type_inputs.contained_vartypes()}
            )
            type_vars_by_name.update(
                {name: StarKind() for name in type_outputs.contained_vartypes()}
            )

            # Construct the type schema of the function
            type_scheme = TypeScheme(
                constraints=constraints or [],
                variables=type_vars_by_name,
                body=GraphType(
                    inputs=type_inputs,
                    outputs=type_outputs,
                ),
            )

            self.functions[func_name] = Function(
                run=wrapped_func,
                declaration=TierkreisFunction(
                    func_name,
                    type_scheme=type_scheme,
                    docs=getdoc(func) or "",
                    input_order=_get_ordered_names(hint_inputs),
                    output_order=_get_ordered_names(hint_outputs),
                ),
            )
            return func

        return decorator


class Worker:
    """Worker server."""

    functions: Dict[str, Function]

    def __init__(self):
        self.functions = {}

    def add_namespace(self, namespace: "Namespace"):
        """Add namespace of functions to workspace."""
        for (name, function) in namespace.functions.items():
            newname = f"{namespace.name}/{name}"
            function.declaration.name = newname
            self.functions[newname] = function

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


class FunctionNotFound(Exception):
    """Function not found."""

    def __init__(self, function):
        super().__init__()
        self.function = function


class DecodeInputError(Exception):
    pass


class EncodeOutputError(Exception):
    pass


@dataclass
class NodeExecutionError(Exception):
    base_exception: Exception


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

        return ps.ListFunctionsResponse(functions=functions)


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


parser = argparse.ArgumentParser(description="Parse worker server cli.")
parser.add_argument(
    "--port", help="If specified listen on network port rather than UDP."
)


def setup_tracing(service_name: str):
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (  # type: ignore
        OTLPSpanExporter,
    )
    from opentelemetry.sdk.resources import SERVICE_NAME, Resource  # type: ignore
    from opentelemetry.sdk.trace import TracerProvider  # type: ignore
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor  # type: ignore

    endpoint = os.environ.get("TIERKREIS_OTLP")

    if endpoint is None:
        return

    tracer_provider = TracerProvider(
        resource=Resource.create({SERVICE_NAME: service_name})
    )

    span_exporter = OTLPSpanExporter(endpoint=endpoint)

    tracer_provider.add_span_processor(SimpleSpanProcessor(span_exporter))

    opentelemetry.trace.set_tracer_provider(tracer_provider)


async def main():
    worker = Worker()
    await worker.start()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
