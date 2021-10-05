"""Send requests to tierkreis server to execute a graph."""
import asyncio
import copy
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from functools import wraps
from typing import Any, Awaitable, Callable, Dict, Optional, Tuple, TypeVar, cast

import aiohttp
import betterproto
import keyring
import tierkreis.core.protos.tierkreis.graph as pg
import tierkreis.core.protos.tierkreis.runtime as pr
import tierkreis.core.protos.tierkreis.signature as ps
from tierkreis.core.function import TierkreisFunction
from tierkreis.core.tierkreis_graph import TierkreisGraph
from tierkreis.core.types import TierkreisTypeErrors
from tierkreis.core.values import IncompatiblePyType, StructValue, TierkreisValue


@dataclass
class RuntimeHTTPError(Exception):
    """Error while communicating with tierkreis server."""

    endpoint: str
    code: int
    content: str

    def __str__(self) -> str:
        return (
            f"Request to endpoint '{self.endpoint}'"
            f" failed with code {self.code}"
            f" and content '{self.content}'."
        )


NamespaceDict = Dict[str, TierkreisFunction]
RuntimeSignature = Dict[str, NamespaceDict]


class _TypeCheckContext:
    """Context manger for type checked graph building."""

    @dataclass
    class TypeInferenceError(Exception):
        """Error when context exit type inference is not succesful."""

        errors: TierkreisTypeErrors

        def __str__(self) -> str:
            return f"Type inference of built graph failed with message:\n {self.errors}"

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
        except TierkreisTypeErrors as err:
            raise self.TypeInferenceError(err)

    async def __aenter__(self) -> TierkreisGraph:
        return self.graph

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        # exeception info not currently used
        # but leaves the option to add context to errors using runtime
        try:
            self.graph._graph = (await self.client.type_check_graph(self.graph))._graph
        except TierkreisTypeErrors as err:
            raise self.TypeInferenceError(err)


@dataclass(frozen=True)
class TaskHandle:
    """Handle for server task"""

    task_id: str


@dataclass
class InputConversionError(Exception):
    input_name: str
    value: Any

    def __str__(self) -> str:
        return (
            f"Input value with name {self.input_name} cannot be"
            "converted to a TierkreisValue."
        )


def _get_myqos_creds() -> Tuple[Optional[str], Optional[str]]:
    keyring_service = "Myqos"
    # TODO DON'T COMMIT ME
    # keyring_service = "myqos-staging"
    login = keyring.get_password(keyring_service, "login")
    password = keyring.get_password(keyring_service, "password")
    return login, password


class RuntimeClient:
    """Client for tierkreis server."""

    def __init__(self, url: str = "http://127.0.0.1:8080") -> None:
        self._url = url

        login, password = _get_myqos_creds()
        if login is None or password is None:
            self.auth = None
        else:
            self.auth = aiohttp.BasicAuth(login, password)
        self._signature_mod = self._get_signature()

    @property
    def signature(self) -> RuntimeSignature:
        return self._signature_mod

    def _get_signature(self) -> RuntimeSignature:
        status, content = async_to_sync(self._get)("/signature")

        if status != 200:
            raise RuntimeHTTPError("signature", status, str(content))

        return signature_from_proto(ps.ListFunctionsResponse().parse(content))

    async def _post(self, path, request):
        async with aiohttp.ClientSession(auth=self.auth) as session:
            async with session.post(
                f"{self._url}{path}",
                data=bytes(request),
                headers={"content-type": "application/protobuf"},
                # uncomment the below for staging test
                # ssl=False,
            ) as response:
                content = await response.content.read()
                return (response.status, content)

    async def _get(self, path):
        async with aiohttp.ClientSession(auth=self.auth) as session:
            async with session.get(
                f"{self._url}{path}",
                headers={"content-type": "application/protobuf"},
                # ssl=False,
            ) as response:
                content = await response.content.read()
                return (response.status, content)

    async def start_task(
        self, graph: TierkreisGraph, py_inputs: Dict[str, Any]
    ) -> TaskHandle:
        """
        Spawn a task that runs a graph and return the task's id. The id can
        later be used to await the completion of the task or cancel its
        execution.

        :param graph: The graph to run.
        :param inputs: The inputs to the graph as map from label to value.
        :return: The id of the running task.
        """
        inputs = {}
        for key, val in py_inputs.items():
            try:
                inputs[key] = TierkreisValue.from_python(val)
            except IncompatiblePyType as err:
                raise InputConversionError(key, val) from err

        status, content = await self._post(
            "/task",
            pr.RunTaskRequest(
                graph=graph.to_proto(),
                inputs=pg.StructValue(map=StructValue(inputs).to_proto_dict()),
            ),
        )

        if status != 200:
            content = content.decode("utf-8")
            raise RuntimeHTTPError("start_task", status, content)

        decoded = pr.RunTaskResponse().parse(content)
        name, _ = betterproto.which_one_of(decoded, "result")

        if name == "task_id":
            return TaskHandle(decoded.task_id)
        raise TierkreisTypeErrors.from_proto(decoded.type_errors)

    async def list_tasks(
        self,
    ) -> Dict[TaskHandle, str]:
        """
        List the id and status for every task on the server.
        """
        status, content = await self._get("/task")

        if status != 200:
            content = content.decode("utf-8")
            raise RuntimeHTTPError("list_task", status, content)

        decoded = pr.ListTasksResponse().parse(content)
        result = {}

        for task in decoded.tasks:
            status_name, _ = betterproto.which_one_of(task, "status")

            if status_name is None:
                status_name = "running"

            result[TaskHandle(task.id)] = status_name

        return result

    def start_task_blocking(
        self, graph: TierkreisGraph, py_inputs: Dict[str, Any]
    ) -> TaskHandle:
        return async_to_sync(self.start_task)(graph, py_inputs)

    async def await_task(self, task: TaskHandle) -> Dict[str, TierkreisValue]:
        """
        Await the completion of a task with a given id.

        :param task: The id of the task to wait for.
        :return: The result of the task.
        """
        status, content = await self._post(
            "/task/await", pr.AwaitTaskRequest(id=task.task_id)
        )

        if status != 200:
            content = content.decode("utf-8")
            raise RuntimeHTTPError("await_task", status, content)

        decoded = pr.AwaitTaskResponse().parse(content)
        status, status_value = betterproto.which_one_of(decoded.task, "status")

        if status != "success":
            raise RuntimeError(f"Task execution failed with message:\n{status_value}")
        assert status_value is not None
        return StructValue.from_proto_dict(status_value.map).values

    def await_task_blocking(self, task: TaskHandle) -> Dict[str, TierkreisValue]:
        return async_to_sync(self.await_task)(task)

    async def delete_task(self, task: TaskHandle):
        """
        Delete a task. Stops the task's execution if it is still running.

        :param task: The id of the task to delete.
        """
        status, content = await self._post(
            "/task/delete", pr.DeleteTaskRequest(id=task.task_id)
        )

        if status != 200:
            content = content.decode("utf-8")
            return RuntimeError("delete_task", status, content)

    def delete_task_blocking(self, task):
        return async_to_sync(self.delete_task)(task)

    async def run_graph(
        self, graph: TierkreisGraph, py_inputs: Dict[str, Any]
    ) -> Dict[str, TierkreisValue]:
        """
        Run a graph and return results. This combines `start_task` and `await_task`.

        :param gb: Graph to run.
        :param inputs: Inputs to graph as map from label to value.
        :return: Outputs as map from label to value.
        """
        task = await self.start_task(graph, py_inputs)
        outputs = await self.await_task(task)
        return outputs

    def run_graph_blocking(
        self, graph: TierkreisGraph, py_inputs: Dict[str, Any]
    ) -> Dict[str, TierkreisValue]:
        return async_to_sync(self.run_graph)(graph, py_inputs)

    async def type_check_graph(self, graph: TierkreisGraph) -> TierkreisGraph:
        value = TierkreisValue.from_python(graph).to_proto()

        status, content = await self._post("/type", ps.InferTypeRequest(value))

        if status != 200:
            content = content.decode("utf-8")
            raise RuntimeHTTPError("type_check_graph", status, content)

        response = ps.InferTypeResponse().parse(content)
        name, message = betterproto.which_one_of(response, "response")

        if name == "success":
            message = cast(ps.InferTypeSuccess, message)
            assert message.value.graph is not None
            return TierkreisValue.from_proto(message.value).to_python(TierkreisGraph)

        errors = cast(ps.TypeErrors, message)
        raise TierkreisTypeErrors.from_proto(errors)

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
    """Starting server locally failed."""


CallableReturn = TypeVar("CallableReturn")


def async_to_sync(
    func: Callable[..., Awaitable[CallableReturn]]
) -> Callable[..., CallableReturn]:
    """
    Converts an asynchronous function into a synchronous one by running it
    on a new async event loop in a newly created thread.
    """

    @wraps(func)
    def sync(*args, **kwargs):
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(lambda: asyncio.run(func(*args, **kwargs)))
            return future.result()

    return sync
