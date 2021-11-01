import asyncio
from typing import AsyncIterator

import pytest

from . import LOCAL_SERVER_PATH

from tierkreis.frontend import RuntimeClient, local_runtime, DockerRuntime


def pytest_addoption(parser):
    parser.addoption(
        "--docker",
        action="store_true",
        help="Whether to use docker container for server rather than local binary",
    )


@pytest.fixture(scope="session")
def event_loop(request):
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def client(request) -> AsyncIterator[RuntimeClient]:
    isdocker = False
    try:
        isdocker = request.config.getoption("--docker") not in (None, False)
    except Exception as _:
        pass
    if isdocker:
        # launch docker container and close at end
        async with DockerRuntime(
            "cqc/tierkreis",
        ) as local_client:
            yield local_client
    else:
        # launch a local server for this test run and kill it at the end
        async with local_runtime(LOCAL_SERVER_PATH) as local_client:
            yield local_client
