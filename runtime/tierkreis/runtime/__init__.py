import asyncio
from grpclib.server import Server
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
            raise KeyError(f"Unknown module {module}")

        if not function in self.modules[module].functions:
            raise KeyError(f"Unknown function {function} in module {module}")

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

class WorkerServerImpl(PythonWorkerBase):
    def __init__(self, worker):
        self.worker = worker

    async def run_python(
        self, module: str, function: str, inputs: Dict[str, "pg.Value"]
    ) -> "RunPythonResponse":
        inputs = core.decode_values(inputs)
        outputs = core.encode_values(self.worker.run(module, function, inputs))
        return RunPythonResponse(outputs = outputs)

async def main():
    worker = Worker()
    await worker.start()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
