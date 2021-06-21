import asyncio
from grpclib.exceptions import GRPCError
from grpclib.server import Server
from grpclib.const import Status as StatusCode
from tierkreis.core.protos.tierkreis.worker import (
    WorkerBase,
    RunFunctionResponse,
    SignatureResponse,
)
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


def snake_to_pascal(name: str) -> str:
    return name.replace("_", " ").title().replace(" ", "")


@dataclass
class Function:
    run: Callable[[StructValue], Awaitable[StructValue]]
    type_scheme: TypeScheme
    docs: Optional[str]


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
                tk_cls = typing.get_origin(type_hints["inputs"])
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

            return_cls = typing.get_origin(return_hint)
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
                        python_inputs = inputs.to_python(hint_inputs)
                    except Exception as error:
                        raise DecodeInputError() from error
                    python_outputs = await func(python_inputs)
                else:
                    python_outputs = await func(
                        **{
                            name: val.to_python(type_hints[name])
                            for name, val in inputs.values.items()
                        }
                    )

                try:
                    outputs = TierkreisValue.from_python(python_outputs)
                except Exception as error:
                    raise EncodeOutputError() from error
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
                docs=getdoc(func),
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

    async def start(self):
        with TemporaryDirectory() as socket_dir:
            # Create a temporary path for a unix domain socket.
            socket_path = "{}/{}".format(socket_dir, "python_worker.sock")

            # Start the python worker gRPC server and bind to the unix domain socket.
            server = Server([WorkerServerImpl(self)])
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


class WorkerServerImpl(WorkerBase):
    def __init__(self, worker):
        self.worker = worker

    async def run_function(
        self, function: str, inputs: Dict[str, "pg.Value"]
    ) -> "RunFunctionResponse":
        try:
            inputs_struct = StructValue.from_proto_dict(inputs)
            outputs_struct = await self.worker.run(function, inputs_struct)
            outputs = outputs_struct.to_proto_dict()
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
        except Exception as err:
            raise GRPCError(
                status=StatusCode.UNKNOWN,
                message=f"Error while running operation: {err}",
            )

    async def signature(self) -> "SignatureResponse":
        entries = [
            pg.SignatureEntry(
                name=function_name,
                type_scheme=function.type_scheme.to_proto(),
                docs=function.docs,
            )
            for (function_name, function) in self.worker.functions.items()
        ]

        return SignatureResponse(entries=entries)


async def main():
    worker = Worker()
    await worker.start()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
