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
from tierkreis.core import PyValMap 
from typing import Dict, Callable, Awaitable, Optional, List, Tuple 
from tempfile import TemporaryDirectory
import sys
import tierkreis.core as core
from dataclasses import dataclass
from inspect import getdoc

@dataclass
class Function:
    run: Callable[[PyValMap], Awaitable[PyValMap]]
    type_scheme: pg.TypeScheme
    docs: Optional[str]

class Namespace:
    name: str
    functions: Dict[str, Function]

    def __init__(self, name: str):
        self.name = name
        self.functions = {}

    def function(
        self,
        name: Optional[str] = None,
        constraints: List[pg.Constraint] = [],
        type_vars: List[Tuple[str, pg.Kind]] = [],
        input_types: Dict[str, pg.Type] = {},
        output_types: Dict[str, pg.Type] = {}
    ):
        def decorator(func):
            func_name = name
            if func_name is None:
                func_name = func.__name__

            async def unpacked_func(inputs: PyValMap) -> PyValMap:
                return await func(**inputs)

            # Construct the type schema of the function
            type_scheme = pg.TypeScheme(
                constraints=constraints,
                variables=[pg.TypeSchemeVar(name=var[0], kind=var[1]) for var in type_vars],
                body=pg.Type(graph=pg.GraphType(
                    inputs=pg.RowType(content=input_types),
                    outputs=pg.RowType(content=output_types),
                ))
            )

            self.functions[func_name] = Function(
                run=unpacked_func,
                type_scheme=type_scheme,
                docs=getdoc(func),
            )
            return unpacked_func

        return decorator


class Worker:
    functions: Dict[str, Function]

    def __init__(self):
        self.functions = {}

    def add_namespace(self, namespace: "Namespace"):
        for (name, function) in namespace.functions.items():
            self.functions[f"{namespace.name}/{name}"] = function

    def run(
        self, function: str, inputs: Dict[str, "core.Value"]
    ) -> Awaitable[Dict[str, "core.Value"]]:
        if function not in self.functions:
            raise FunctionNotFound(function)

        f = self.functions[function]

        return f.run(inputs)

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


class WorkerServerImpl(WorkerBase):
    def __init__(self, worker):
        self.worker = worker

    async def run_function(
        self, function: str, inputs: Dict[str, "pg.Value"]
    ) -> "RunFunctionResponse":
        try:
            py_inputs = core.decode_values(inputs)
        except ValueError as err:
            raise GRPCError(
                status=StatusCode.INVALID_ARGUMENT,
                message="Error while decoding inputs",
            ) from err

        try:
            outputs = await self.worker.run(function, py_inputs)
        except FunctionNotFound:
            raise GRPCError(
                status=StatusCode.UNIMPLEMENTED,
                message=f"Unsupported operation: {function}'",
            )
        except Exception as err:
            raise GRPCError(
                status=StatusCode.UNKNOWN,
                message=f"Error while running operation: {err}",
            )

        outputs = core.encode_values(outputs)
        return RunFunctionResponse(outputs=outputs)

    async def signature(self) -> "SignatureResponse":
        entries = [
            pg.SignatureEntry(
                name=function_name,
                type_scheme=function.type_scheme,
                docs=function.docs
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
