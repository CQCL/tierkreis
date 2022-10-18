import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator, Callable

import pytest

from tierkreis.core.signature import Signature
from tierkreis.frontend import docker_runtime, local_runtime, myqos_runtime
from tierkreis.frontend.builder import Namespace
from tierkreis.frontend.python_runtime import PyRuntime
from tierkreis.frontend.runtime_client import RuntimeClient, ServerRuntime

from . import LOCAL_SERVER_PATH
from .test_worker import main


def pytest_addoption(parser):
    parser.addoption(
        "--docker",
        action="store_true",
        help="Whether to use docker container for server rather than local binary",
    )
    parser.addoption(
        "--myqos",
        action="store_true",
        help="Whether to use the myqos runtime for testing",
    )
    parser.addoption(
        "--myqos-staging",
        action="store_true",
        help="Use the myqos runtime from staging area (implies --myqos)",
    )
    parser.addoption(
        "--server-logs",
        action="store_true",
        help="Whether to attempt to print server logs (for debugging).",
    )
    parser.addoption(
        "--pytket",
        action="store_true",
        default=False,
        help="Run pytket integration tests",
    )


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
    return PyRuntime([main.namespace])


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
    ismyqos = False
    ismyqos_staging = False
    try:
        isdocker = request.config.getoption("--docker") not in (None, False)
        ismyqos = request.config.getoption("--myqos") not in (None, False)
        ismyqos_staging = request.config.getoption("--myqos-staging") not in (
            None,
            False,
        )
    except Exception as _:
        pass
    if isdocker:
        # launch docker container and close at end
        async with docker_runtime(
            "cqc/tierkreis",
        ) as local_client:
            yield local_client
    elif ismyqos_staging:
        async with myqos_runtime(
            "tierkreistrr595bx-pr.uksouth.cloudapp.azure.com",
            staging_creds=True,
        ) as myqos_client:
            yield myqos_client
    elif ismyqos:
        async with myqos_runtime("tierkreis.myqos.com") as myqos_client:
            yield myqos_client
    else:
        # launch a local server for this test run and kill it at the end
        async with local_runtime_launcher() as client:
            yield client


@pytest.fixture(scope="session")
def local_runtime_launcher(request) -> Callable:
    try:
        logs = request.config.getoption("--server-logs") not in (None, False)
    except Exception:
        logs = False

    @asynccontextmanager
    async def foo(**kwarg_overrides: Any) -> AsyncIterator[ServerRuntime]:
        kwargs = {
            "workers": [("python", Path(__file__).parent / "test_worker")],
            "worker_uris": [],
            "show_output": logs,
            **kwarg_overrides,
        }
        async with local_runtime(LOCAL_SERVER_PATH, **kwargs) as client:  # type: ignore
            yield client

    return foo


@pytest.fixture()
async def sig(client: RuntimeClient) -> Signature:
    return await client.get_signature()


@pytest.fixture()
def bi(sig: Signature) -> Namespace:
    return Namespace(sig)
