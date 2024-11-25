import asyncio
import sys
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any, AsyncIterator, Callable

import pytest
from tierkreis.builder import Namespace
from tierkreis.client.runtime_client import RuntimeClient
from tierkreis.client.server_client import ServerRuntime
from tierkreis.core.signature import Signature
from tierkreis.pyruntime import PyRuntime

from . import LOCAL_SERVER_PATH, PYTHON_TESTS_DIR, PYTHON_WORKER
from .managers.local_manager import local_runtime

sys.path.append(str(PYTHON_TESTS_DIR))
from test_worker import main  # type: ignore # noqa: E402

if TYPE_CHECKING:
    from grpclib.client import Channel


def pytest_addoption(parser):
    parser.addoption(
        "--docker",
        action="store_true",
        help="Whether to use docker container for server rather than local binary",
    )
    parser.addoption(
        "--server-logs",
        action="store_true",
        help="Whether to attempt to print server logs (for debugging).",
    )


@pytest.fixture(scope="session")
def event_loop(request):
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def pyruntime():
    return PyRuntime([main.root])


@pytest.fixture(scope="session", params=[False, True])
async def client(request, server_client, pyruntime) -> RuntimeClient:
    # if parameter is true, return python runtime
    if request.param:
        return pyruntime
    else:
        return server_client


@pytest.fixture(scope="session")
async def server_client(
    request, local_runtime_launcher
) -> AsyncIterator[ServerRuntime]:
    isdocker = False
    try:
        isdocker = request.config.getoption("--docker") not in (None, False)
    except Exception as _:
        pass
    if isdocker:
        # launch docker container and close at end
        from .managers.docker_manager import docker_runtime

        async with docker_runtime(
            "cqc/tierkreis",
        ) as local_client:
            yield local_client
    else:
        # launch a local server for this test run and kill it at the end
        async with local_runtime_launcher(
            workers=[("python", PYTHON_WORKER)]
        ) as client:
            yield client


def _local_channel_launcher(request) -> Callable:
    try:
        logs = request.config.getoption("--server-logs") not in (None, False)
    except Exception:
        logs = False

    @asynccontextmanager
    async def launch_with_overrides(**kwarg_overrides: Any) -> AsyncIterator["Channel"]:
        kwargs = {
            "workers": [],
            "worker_uris": [],
            "show_output": logs,
            **kwarg_overrides,
        }
        async with local_runtime(LOCAL_SERVER_PATH, **kwargs) as channel:
            yield channel

    return launch_with_overrides


@pytest.fixture(scope="session")
def local_runtime_launcher(request) -> Callable:
    @asynccontextmanager
    async def launch_with_overrides(
        **kwarg_overrides: Any,
    ) -> AsyncIterator[ServerRuntime]:
        async with _local_channel_launcher(request)(**kwarg_overrides) as channel:
            yield ServerRuntime(channel)

    return launch_with_overrides


@pytest.fixture()
async def sig(client: RuntimeClient) -> Signature:
    return await client.get_signature()


@pytest.fixture()
def bi(sig: Signature) -> Namespace:
    return Namespace(sig)
