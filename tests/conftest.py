import asyncio
from typing import AsyncIterator

import pytest
from grpclib.client import Channel
from test_worker import main

from tierkreis.builder import Namespace
from tierkreis.client.runtime_client import RuntimeClient
from tierkreis.client.server_client import RuntimeClient, ServerRuntime
from tierkreis.core.signature import Signature
from tierkreis.core.tierkreis_graph import TierkreisGraph
from tierkreis.pyruntime import PyRuntime


def pytest_addoption(parser):
    parser.addoption(
        "--host",
        action="store",
        help="Remote server host",
    )
    parser.addoption(
        "--port",
        action="store",
        help="Server port",
    )
    parser.addoption(
        "--pytket",
        action="store_true",
        default=False,
        help="Run pytket integration tests",
    )
    parser.addoption(
        "--client-only",
        action="store_true",
        default=False,
        help="Only run tests that use the client fixture",
    )


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--client-only"):
        return
    skip_non_client = pytest.mark.skip(reason="Doesn't use client fixture")
    for item in items:
        if "client" not in getattr(item, "fixturenames", ()):
            item.add_marker(skip_non_client)


def pytest_configure(config):
    if not config.option.pytket:
        setattr(config.option, "markexpr", "not pytket")


@pytest.fixture(scope="session")
def event_loop(request):
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def pyruntime():
    return PyRuntime([main.root])


@pytest.fixture(scope="session")
async def client(request, pyruntime) -> AsyncIterator[RuntimeClient]:
    host = request.config.getoption("--host", "")
    port = request.config.getoption("--port", "")

    if host and port:
        async with Channel(host, int(port)) as c:
            yield ServerRuntime(c)
    else:
        yield pyruntime


@pytest.fixture()
async def sig(client: RuntimeClient) -> Signature:
    return await client.get_signature()


@pytest.fixture()
def bi(sig: Signature) -> Namespace:
    return Namespace(sig)


@pytest.fixture()
def idpy_graph() -> TierkreisGraph:
    tk_g = TierkreisGraph()

    id_node = tk_g.add_func("python_nodes::id_py", value=tk_g.input["id_in"])
    tk_g.set_outputs(id_out=id_node)

    return tk_g
