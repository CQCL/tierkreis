from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict
from urllib.parse import urlparse

from grpclib.client import Channel

import tierkreis.core.protos.tierkreis.v1alpha1.runtime as pr
from tierkreis.client.runtime_client import RuntimeClient
from tierkreis.client.server_client import ServerRuntime
from tierkreis.core.signature import Signature
from tierkreis.core.tierkreis_graph import Location, TierkreisGraph
from tierkreis.core.values import TierkreisValue


class Callback(RuntimeClient):
    def __init__(self, channel: Channel, loc: Location):
        self.runtime = ServerRuntime(channel)
        self.loc = loc

    async def get_signature(self) -> Signature:
        return await self.runtime.get_signature(self.loc)

    async def run_graph(
        self,
        graph: TierkreisGraph,
        /,
        **py_inputs: Any,
    ) -> Dict[str, TierkreisValue]:
        return await self.runtime.run_graph(graph, self.loc, **py_inputs)

    async def type_check_graph(self, graph: TierkreisGraph) -> TierkreisGraph:
        return await self.runtime.type_check_graph(graph, self.loc)


@asynccontextmanager
async def callback_server(callback: pr.Callback) -> AsyncIterator[RuntimeClient]:
    url = urlparse(callback.uri)
    host, port = url.hostname, url.port
    assert host is not None
    async with Channel(host, port) as channel:
        yield Callback(channel, callback.loc)
