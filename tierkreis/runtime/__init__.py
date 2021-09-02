import asyncio
import grpclib
import grpclib.server
import grpclib.events
from grpclib.exceptions import GRPCError
from grpclib.server import Server
from grpclib.const import Status as StatusCode
from tierkreis.core.protos.tierkreis.worker import (
    WorkerBase,
    RunFunctionResponse,
)
import tierkreis.core.protos.tierkreis.signature as ps
import tierkreis.core.protos.tierkreis.graph as pg
from tierkreis.core.types import (
    Constraint,
    Kind,
    TypeScheme,
    Row,
    GraphType,
)
from tierkreis.core.values import (
    TierkreisValue,
    StructValue,
)
from dataclasses import make_dataclass, is_dataclass
from tierkreis.core.tierkreis_struct import TierkreisStruct
from typing import (
    Dict,
    Callable,
    Awaitable,
    Optional,
    List,
    Tuple,
    Any,
    Type,
    cast,
    Union,
)
import typing
from tempfile import TemporaryDirectory
import sys
from dataclasses import dataclass
from inspect import getdoc, isclass
import argparse
import opentelemetry.trace
import os
import opentelemetry.context
from opentelemetry.semconv.trace import SpanAttributes
import opentelemetry.propagate

tracer = opentelemetry.trace.get_tracer(__name__)


def snake_to_pascal(name: str) -> str:
    return name.replace("_", " ").title().replace(" ", "")


@dataclass
class Function:
    run: Callable[[StructValue], Awaitable[StructValue]]
    type_scheme: TypeScheme
    description: Optional[str]


class Namespace:
    name: str
    functions: Dict[str, Function]

    def __init__(self, name: str):
        self.name = name
        self.functions = dict()

    def function(
        self,
        name: Optional[str] = None,
        constraints: List[Constraint] = [],
        type_vars: Dict[Union[str, typing.TypeVar], Kind] = {},
    ):
        def decorator(func):
            func_name = name
            if func_name is None:
                func_name = func.__name__

            # Get input and output type hints
            type_hints = typing.get_type_hints(func)

            if "return" not in type_hints:
                raise ValueError("Tierkreis function needs return type hint.")
            return_hint = type_hints.pop("return")

            struct_input = False

            if "inputs" in type_hints:
                tk_cls = type_hints["inputs"]
                origin = typing.get_origin(tk_cls)
                tk_cls = origin if origin is not None else tk_cls
                struct_input = (
                    tk_cls is not None
                    and isclass(tk_cls)
                    and issubclass(tk_cls, TierkreisStruct)
                )
            if struct_input:
                hint_inputs = type_hints["inputs"]
            else:
                hint_inputs = make_dataclass(
                    f"{snake_to_pascal(func_name)}Inputs", type_hints.items()
                )

            origin = typing.get_origin(return_hint)
            return_cls = origin if origin is not None else return_hint
            struct_output = False
            if (
                return_cls is not None
                and isclass(return_cls)
                and issubclass(return_cls, TierkreisStruct)
            ):
                hint_outputs = return_hint
                struct_output = True
            else:
                hint_outputs = make_dataclass(
                    f"{snake_to_pascal(func_name)}Outputs", [("value", return_hint)]
                )

            # Convert type hints into tierkreis types
            type_inputs = Row.from_python(hint_inputs)
            type_outputs = Row.from_python(hint_outputs)

            # Wrap function with input and output conversions
            async def wrapped_func(inputs: StructValue) -> StructValue:
                if struct_input:
                    try:
                        with tracer.start_as_current_span(
                            "decoding inputs to python type"
                        ):
                            python_inputs = inputs.to_python(hint_inputs)
                    except Exception as error:
                        raise DecodeInputError(str(error)) from error
                    try:
                        python_outputs = await func(python_inputs)
                    except Exception as error:
                        raise NodeExecutionError(str(error)) from error
                else:
                    try:
                        with tracer.start_as_current_span(
                            "decoding inputs to python type"
                        ):
                            python_inputs = {
                                name: val.to_python(type_hints[name])
                                for name, val in inputs.values.items()
                            }
                    except Exception as error:
                        raise DecodeInputError(str(error)) from error

                    try:
                        python_outputs = await func(**python_inputs)
                    except Exception as error:
                        raise NodeExecutionError(str(error)) from error

                try:
                    with tracer.start_as_current_span(
                        "encoding outputs from python type"
                    ):
                        outputs = TierkreisValue.from_python(python_outputs)
                except Exception as error:
                    raise EncodeOutputError(str(error)) from error
                if struct_output:
                    return cast(StructValue, outputs)
                else:
                    return StructValue({"value": outputs})

            # Convert the type vars to names
            def type_var_to_name(type_var: Union[str, typing.TypeVar]) -> str:
                if isinstance(type_var, typing.TypeVar):
                    return type_var.__name__
                else:
                    return type_var

            type_vars_by_name = {
                type_var_to_name(var): kind for var, kind in type_vars.items()
            }

            # Construct the type schema of the function
            type_scheme = TypeScheme(
                constraints=constraints,
                variables=type_vars_by_name,
                body=GraphType(
                    inputs=type_inputs,
                    outputs=type_outputs,
                ),
            )

            self.functions[func_name] = Function(
                run=wrapped_func,
                type_scheme=type_scheme,
                description=getdoc(func),
            )
            return func

        return decorator


class Worker:
    functions: Dict[str, Function]

    def __init__(self):
        self.functions = {}

    def add_namespace(self, namespace: "Namespace"):
        for (name, function) in namespace.functions.items():
            self.functions[f"{namespace.name}/{name}"] = function

    def run(self, function: str, inputs: StructValue) -> Awaitable[StructValue]:
        if function not in self.functions:
            raise FunctionNotFound(function)

        f = self.functions[function]

        # See https://github.com/python/mypy/issues/5485
        return cast(Any, f).run(inputs)

    async def start(self, port: Optional[str] = None):
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
                socket_path = "{}/{}".format(socket_dir, "python_worker.sock")

                # Start the python worker gRPC server and bind to the unix domain socket.
                await server.start(path=socket_path)

                # Print the path of the unix domain socket to stdout so the runtime can
                # connect to it. Without the flush the runtime did not receive the
                # socket path and blocked indefinitely.
                print(socket_path)
                sys.stdout.flush()

                await server.wait_closed()


class FunctionNotFound(Exception):
    def __init__(self, function):
        self.function = function


class DecodeInputError(Exception):
    pass


class EncodeOutputError(Exception):
    pass


class NodeExecutionError(Exception):
    pass


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
            )
        except EncodeOutputError as err:
            raise GRPCError(
                status=StatusCode.INTERNAL,
                message=f"Error while encoding outputs: {err}",
            )
        except FunctionNotFound as err:
            raise GRPCError(
                status=StatusCode.UNIMPLEMENTED,
                message=f"Unsupported function: {function}",
            )
        except NodeExecutionError as err:
            raise GRPCError(
                status=StatusCode.UNKNOWN,
                message=f"Error while running operation: {err}",
            )


class SignatureServerImpl(ps.SignatureBase):
    worker: Worker

    def __init__(self, worker: Worker):
        self.worker = worker

    async def list_functions(self) -> "ps.ListFunctionsResponse":
        functions = {
            function_name: ps.FunctionDeclaration(
                name=function_name,
                type_scheme=function.type_scheme.to_proto(),
                description=function.description or "",
            )
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
    pass


parser = argparse.ArgumentParser(description="Parse worker server cli.")
parser.add_argument(
    "--port", help="If specified listen on network port rather than UDP."
)


def setup_tracing(service_name: str):
    from opentelemetry import trace
    from opentelemetry.sdk.resources import SERVICE_NAME, Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

    endpoint = os.environ.get("TIERKREIS_OTLP")

    if endpoint is None:
        return

    tracer_provider = TracerProvider(
        resource=Resource.create({SERVICE_NAME: service_name})
    )

    span_exporter = OTLPSpanExporter(endpoint=endpoint)

    tracer_provider.add_span_processor(SimpleSpanProcessor(span_exporter))

    trace.set_tracer_provider(tracer_provider)


async def main():
    worker = Worker()
    await worker.start()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
