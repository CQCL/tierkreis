"""Send requests to tierkreis server to execute a graph."""
import asyncio
from collections.abc import Coroutine
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from functools import wraps
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Type,
    TypeVar,
    cast,
)

import betterproto
from grpclib.client import Channel
from grpclib.events import SendRequest

import tierkreis.core.protos.tierkreis.v1alpha1.graph as pg
import tierkreis.core.protos.tierkreis.v1alpha1.runtime as pr
import tierkreis.core.protos.tierkreis.v1alpha1.signature as ps
from tierkreis.client.runtime_client import RuntimeClient
from tierkreis.core.signature import Signature
from tierkreis.core.tierkreis_graph import Location, TierkreisGraph
from tierkreis.core.type_errors import TierkreisTypeErrors
from tierkreis.core.values import IncompatiblePyValue, StructValue, TierkreisValue

if TYPE_CHECKING:
    from betterproto.grpc.grpclib_client import ServiceStub


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


@dataclass
class InputConversionError(Exception):
    input_name: str
    value: Any

    def __str__(self) -> str:
        return (
            f"Input value with name {self.input_name} cannot be"
            "converted to a TierkreisValue."
        )


StubType = TypeVar("StubType", bound="ServiceStub")


class ServerRuntime(RuntimeClient):
    """Client for tierkreis server."""

    def __init__(self, channel: "Channel") -> None:
        self._channel = channel
        self._stubs: dict[str, ServiceStub] = {}

    def socket_address(self) -> str:
        return f"{self._channel._host}:{self._channel._port}"

    def _stub_gen(self, key: str, stub_t: Type[StubType]) -> StubType:
        if key not in self._stubs:
            self._stubs[key] = stub_t(self._channel)
        stub = self._stubs[key]
        assert isinstance(stub, stub_t)
        return stub

    @property
    def _signature_stub(self) -> ps.SignatureStub:
        return self._stub_gen("signature", ps.SignatureStub)

    @property
    def _runtime_stub(self) -> pr.RuntimeStub:
        return self._stub_gen("runtime", pr.RuntimeStub)

    @property
    def _type_stub(self) -> ps.TypeInferenceStub:
        return self._stub_gen("type", ps.TypeInferenceStub)

    async def get_signature(self, loc: Location = Location([])) -> Signature:
        return Signature.from_proto(
            await self._signature_stub.list_functions(ps.ListFunctionsRequest(loc))
        )

    async def run_graph(
        self,
        graph: TierkreisGraph,
        loc: Location = Location([]),
        /,
        **py_inputs: Any,
    ) -> Dict[str, TierkreisValue]:
        """
        Run a graph and return results.

        :param gb: Graph to run.
        :param inputs: Inputs to graph as map from label to value.
        :param type_check: Whether to type check the graph.
        :return: Outputs as map from label to value.
        """
        inputs = {}
        for key, val in py_inputs.items():
            try:
                inputs[key] = TierkreisValue.from_python(val)
            except IncompatiblePyValue as err:
                raise InputConversionError(key, val) from err

        decoded = await self._runtime_stub.run_graph(
            pr.RunGraphRequest(
                graph=graph.to_proto(),
                inputs=pg.StructValue(map=StructValue(inputs).to_proto_dict()),
                type_check=True,
                loc=loc,
            )
        )

        status, status_value = betterproto.which_one_of(decoded, "result")
        assert status_value is not None
        if status == "type_errors":
            raise TierkreisTypeErrors.from_proto(status_value, graph)
        if status == "error":
            raise RuntimeError(
                f"Run_graph execution failed with message:\n{status_value}"
            )
        return StructValue.from_proto_dict(status_value.map).values

    def run_graph_block(
        self,
        graph: TierkreisGraph,
        /,
        **py_inputs: Any,
    ) -> Dict[str, TierkreisValue]:
        async def _run(
            host: str,
            port: int,
        ):
            async with Channel(host, port) as channel:
                return await ServerRuntime(channel).run_graph(graph, **py_inputs)

        return async_to_sync(_run)(self._channel._host, self._channel._port)

    async def type_check_graph(
        self, graph: TierkreisGraph, loc: Location = Location([])
    ) -> TierkreisGraph:
        value = TierkreisValue.from_python(graph).to_proto()

        response = await self._type_stub.infer_type(
            ps.InferTypeRequest(value=value, loc=loc)
        )
        name, message = betterproto.which_one_of(response, "response")

        if name == "success":
            message = cast(ps.InferTypeSuccess, message)
            assert message.value.graph is not None
            return TierkreisValue.from_proto(message.value).to_python(TierkreisGraph)

        errors = cast(ps.TypeErrors, message)
        raise TierkreisTypeErrors.from_proto(errors, graph)


def _gen_auth_injector(login: str, pwd: str) -> Callable[["SendRequest"], Coroutine]:
    async def _inject_auth(event: SendRequest) -> None:
        event.metadata["token"] = login
        event.metadata["key"] = pwd

    return _inject_auth


class RuntimeLaunchFailed(Exception):
    """Starting server locally failed."""


CallableReturn = TypeVar("CallableReturn")


def async_to_sync(
    func: Callable[..., Coroutine[None, None, CallableReturn]],
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
