"""Send requests to tierkreis server to execute a graph."""
from typing import (
    Dict,
    IO,
    Iterator,
    List,
    cast,
    Optional,
    Callable,
    Awaitable,
    TypeVar,
)
from dataclasses import dataclass
import copy
from contextlib import contextmanager
from pathlib import Path
import subprocess
import requests
import betterproto
from tierkreis.core.tierkreis_graph import TierkreisGraph
from tierkreis.core.function import TierkreisFunction
from tierkreis.core.values import TierkreisValue, StructValue
import tierkreis.core.protos.tierkreis.graph as pg
import tierkreis.core.protos.tierkreis.runtime as pr
import tierkreis.core.protos.tierkreis.signature as ps
import sys
import aiohttp
import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import wraps


@dataclass
class RuntimeHTTPError(Exception):
    endpoint: str
    code: int

    def __str__(self) -> str:
        return (
            f"Request to endpoint '{self.endpoint}'" f" failed with code {self.code}."
        )


NamespaceDict = Dict[str, TierkreisFunction]
RuntimeSignature = Dict[str, NamespaceDict]


class _TypeCheckContext:
    """Context manger for type checked graph building."""

    @dataclass
    class TypeInferenceError(Exception):
        """Error when context exit type inference is not succesful."""

        message: str

        def __str__(self) -> str:
            return (
                f"Type inference of built graph failed with message:\n {self.message}"
            )

    def __init__(
        self, client: "RuntimeClient", initial_graph: Optional[TierkreisGraph] = None
    ) -> None:
        self.client = client
        self.graph = (
            TierkreisGraph() if initial_graph is None else copy.deepcopy(initial_graph)
        )

    def __enter__(self) -> TierkreisGraph:
        return self.graph

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        try:
            self.graph._graph = self.client.type_check_graph_blocking(self.graph)._graph
        except RuntimeClient.RuntimeTypeError as err:
            raise self.TypeInferenceError(err.message)

    async def __aenter__(self) -> TierkreisGraph:
        return self.graph

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        # exeception info not currently used
        # but leaves the option to add context to errors using runtime
        try:
            self.graph._graph = (await self.client.type_check_graph(self.graph))._graph
        except RuntimeClient.RuntimeTypeError as err:
            raise self.TypeInferenceError(err.message)


@dataclass(frozen=True)
class TaskHandle:
    id: int


class RuntimeClient:
    @dataclass
    class RuntimeTypeError(Exception):
        message: str

    def __init__(self, url: str = "http://127.0.0.1:8080") -> None:
        self._url = url
        self._signature_mod = self._get_signature()

    @property
    def signature(self) -> RuntimeSignature:
        return self._signature_mod

    def _get_signature(self) -> RuntimeSignature:
        resp = requests.get(
            self._url + "/signature",
            headers={"content-type": "application/protobuf"},
        )
        if resp.status_code != 200:
            raise RuntimeHTTPError("signature", resp.status_code)

        return signature_from_proto(ps.ListFunctionsResponse().parse(resp.content))

    async def _post(self, path, request):
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self._url}{path}",
                data=bytes(request),
                headers={"content-type": "application/protobuf"},
            ) as response:
                content = await response.content.read()
                return (response.status, content)

    async def _get(self, path):
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self._url}{path}",
                headers={"content-type": "application/protobuf"},
            ) as response:
                content = await response.content.read()
                return (response.status, content)

    async def start_task(
        self, graph: TierkreisGraph, inputs: Dict[str, TierkreisValue]
    ) -> TaskHandle:
        """
        Spawn a task that runs a graph and return the task's id. The id can
        later be used to await the completion of the task or cancel its
        execution.

        :param graph: The graph to run.
        :param inputs: The inputs to the graph as map from label to value.
        :return: The id of the running task.
        """
        status, content = await self._post(
            "/task",
            pr.RunTaskRequest(
                graph=graph.to_proto(),
                inputs=pg.StructValue(map=StructValue(inputs).to_proto_dict()),
            ),
        )

        if status != 200:
            raise RuntimeHTTPError("start_task", status)

        decoded = pr.RunTaskResponse().parse(content)
        return TaskHandle(decoded.id)

    async def list_tasks(
        self,
    ) -> Dict[TaskHandle, str]:
        """
        List the id and status for every task on the server.
        """
        status, content = await self._get("/task")

        if status != 200:
            raise RuntimeHTTPError("list_task", status)

        decoded = pr.ListTasksResponse().parse(content)
        result = {}

        for task in decoded.tasks:
            status_name, _ = betterproto.which_one_of(task, "status")

            if status_name is None:
                status_name = "running"

            result[task.id] = status_name

        return result

    def start_task_blocking(
        self, graph: TierkreisGraph, inputs: Dict[str, TierkreisValue]
    ) -> TaskHandle:
        return async_to_sync(self.start_task)(graph, inputs)

    async def await_task(self, task: TaskHandle) -> Dict[str, TierkreisValue]:
        """
        Await the completion of a task with a given id.

        :param task: The id of the task to wait for.
        :return: The result of the task.
        """
        status, content = await self._post(
            "/task/await", pr.AwaitTaskRequest(id=task.id)
        )
        if status != 200:
            raise RuntimeHTTPError("await_task", status)
        decoded = pr.AwaitTaskResponse().parse(content)
        status, status_value = betterproto.which_one_of(decoded.task, "status")

        if status != "success":
            raise RuntimeError(f"Task execution failed with message:\n{status_value}")

        return StructValue.from_proto_dict(status_value.map).values

    def await_task_blocking(self, task: TaskHandle) -> Dict[str, TierkreisValue]:
        return async_to_sync(self.await_task)(task)

    async def delete_task(self, task: TaskHandle):
        """
        Delete a task. Stops the task's execution if it is still running.

        :param task: The id of the task to delete.
        """
        status, _ = await self._post("/task/delete", pr.DeleteTaskRequest(id=task.id))

        if status != 200:
            return RuntimeError("delete_task", status)

    def delete_task_blocking(self, task):
        return async_to_sync(self.delete_task)(task)

    async def run_graph(
        self, graph: TierkreisGraph, inputs: Dict[str, TierkreisValue]
    ) -> Dict[str, TierkreisValue]:
        """
        Run a graph and return results. This combines `start_task` and `await_task`.

        :param gb: Graph to run.
        :param inputs: Inputs to graph as map from label to value.
        :return: Outputs as map from label to value.
        """
        task = await self.start_task(graph, inputs)
        outputs = await self.await_task(task)
        return outputs

    def run_graph_blocking(
        self, graph: TierkreisGraph, inputs: Dict[str, TierkreisValue]
    ) -> Dict[str, TierkreisValue]:
        return async_to_sync(self.run_graph)(graph, inputs)

    async def type_check_graph(self, graph: TierkreisGraph) -> TierkreisGraph:
        value = TierkreisValue.from_python(graph).to_proto()

        status, content = await self._post("/type", ps.InferTypeRequest(value))

        if status != 200:
            raise RuntimeHTTPError("type_check_graph", status)

        response = ps.InferTypeResponse().parse(content)
        name, message = betterproto.which_one_of(response, "response")

        if name == "success":
            message = cast(ps.InferTypeSuccess, message)
            assert message.value.graph is not None
            return TierkreisValue.from_proto(message.value).to_python(TierkreisGraph)
        raise self.RuntimeTypeError(str(message))

    def type_check_graph_blocking(self, graph: TierkreisGraph) -> TierkreisGraph:
        return async_to_sync(self.type_check_graph)(graph)

    def build_graph(
        self, initial_graph: Optional[TierkreisGraph] = None
    ) -> _TypeCheckContext:
        return _TypeCheckContext(self, initial_graph)


def signature_from_proto(pr_sig: ps.ListFunctionsResponse) -> RuntimeSignature:
    namespaces: Dict[str, Dict[str, TierkreisFunction]] = dict()

    for name, entry in pr_sig.functions.items():
        namespace, fname = name.split("/", 2)
        func = TierkreisFunction.from_proto(entry)
        if namespace in namespaces:
            namespaces[namespace][fname] = func
        else:
            namespaces[namespace] = {fname: func}

    return namespaces


class RuntimeLaunchFailed(Exception):
    pass


T = TypeVar("T")


def async_to_sync(f: Callable[..., Awaitable[T]]) -> Callable[..., T]:
    """
    Converts an asynchronous function into a synchronous one by running it
    on a new async event loop in a newly created thread.
    """

    @wraps(f)
    def sync(*args, **kwargs):
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(lambda: asyncio.run(f(*args, **kwargs)))
            return future.result()

    return sync


@contextmanager
def local_runtime(
    executable: Path,
    workers: List[Path],
    http_port: str = "8080",
    grpc_port: str = "9090",
    show_output: bool = False,
) -> Iterator[RuntimeClient]:
    """Provide a context for a local runtime running in a subprocess.

    :param executable: Path to server binary
    :type executable: Path
    :param workers: Paths of worker servers
    :type workers: List[Path]
    :param http_port: Localhost http port, defaults to "8080"
    :type http_port: str, optional
    :param grpc_port: Localhost grpc port, defaults to "9090"
    :type grpc_port: str, optional
    :param show_output: Show server tracing/errors, defaults to False
    :type show_output: bool, optional
    :yield: RuntimeClient
    :rtype: Iterator[RuntimeClient]
    """
    command = [executable, "--http", http_port, "--grpc", grpc_port]
    for worker in workers:
        command.extend(["--worker-path", worker])

    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    lines = []
    for line in cast(IO[bytes], proc.stdout):
        lines.append(line)
        if "Starting grpc server" in str(line):
            # server is ready to receive requests
            break

    def write_process_out(process: subprocess.Popen) -> None:
        # get remaining output
        out, errs = process.communicate()

        if errs:
            sys.stderr.buffer.write(errs)
        for line in lines:
            sys.stdout.buffer.write(line)
        if out:
            sys.stdout.buffer.write(out)

    if proc.poll() is not None:
        # process has terminated unexpectedly
        write_process_out(proc)
        raise RuntimeLaunchFailed()

    try:
        yield RuntimeClient(f"http://127.0.0.1:{http_port}")
    finally:
        if show_output:
            proc.terminate()
            write_process_out(proc)
        proc.kill()
