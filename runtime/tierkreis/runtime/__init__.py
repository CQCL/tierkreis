import asyncio
from grpclib.exceptions import GRPCError
from grpclib.server import Server
from grpclib.const import Status as StatusCode
from tierkreis.core.protos.tierkreis.python_worker import PythonWorkerBase, RunPythonResponse
import tierkreis.core.protos.tierkreis.graph as pg
from typing import Dict, Tuple
from tempfile import TemporaryDirectory
import sys
import functools
import typing
import tierkreis.core as core

class Module:
    def __init__(self, name: str):
        self.name = name
        self.functions = {}

    def function(self, name = None):
        def decorator(func):
            func_name = name
            if func_name == None:
                func_name = func.__name__

            self.functions[func_name] = func
            return func
        return decorator

class Worker:
    def __init__(self):
        self.modules = {}

    def add_module(self, module: "Module"):
        self.modules[module.name] = module

    def run(
        self,
        module: str,
        function: str,
        inputs: Dict[str, "core.Value"]
    ) -> Dict[str, "core.Value"]:
        if not module in self.modules:
            raise FunctionNotFound(module, function)

        if not function in self.modules[module].functions:
            raise FunctionNotFound(module, function)

        f = self.modules[module].functions[function]

        return f(inputs)

    async def start(self):
        with TemporaryDirectory() as socket_dir:
            # Create a temporary path for a unix domain socket.
            socket_path = "{}/{}".format(socket_dir, "python_worker.sock")

            # Start the python worker gRPC server and bind to the unix domain socket.
            server = Server([WorkerServerImpl(self)])
            await server.start(path = socket_path)

            # Print the path of the unix domain socket to stdout so the runtime can
            # connect to it. Without the flush the runtime did not receive the
            # socket path and blocked indefinitely.
            print(socket_path)
            sys.stdout.flush()

            await server.wait_closed()

class FunctionNotFound(Exception):
    def __init__(self, module, function):
        self.module = module
        self.function = function

class WorkerServerImpl(PythonWorkerBase):
    def __init__(self, worker):
        self.worker = worker

    async def run_python(
        self, module: str, function: str, inputs: Dict[str, "pg.Value"]
    ) -> "RunPythonResponse":
        inputs = core.decode_values(inputs)

        try:
            outputs = self.worker.run(module, function, inputs)
        except FunctionNotFound:
            raise GRPCError(
                status = StatusCode.UNIMPLEMENTED,
                message = f"Unsupported operation: {module}/{function}'"
            )
        except Exception as err:
            raise GRPCError(
                status = StatusCode.UNKNOWN,
                message = f"Error while running operation: {err}"
            )

        outputs = core.encode_values(outputs)
        return RunPythonResponse(outputs = outputs)

async def main():
    worker = Worker()
    await worker.start()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
