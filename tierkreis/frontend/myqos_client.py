from contextlib import asynccontextmanager
from typing import Optional, Tuple

import keyring
from grpclib.client import Channel
from grpclib.events import SendRequest, listen

from .runtime_client import RuntimeClient, _gen_auth_injector


def _get_myqos_creds(staging: bool = False) -> Tuple[Optional[str], Optional[str]]:
    keyring_service = "myqos-staging" if staging else "Myqos"
    login = keyring.get_password(keyring_service, "login")
    password = keyring.get_password(keyring_service, "password")
    return login, password


class MyqosClient(RuntimeClient):
    """Runtime client for use with tierkreis hosted on mushroom.
    Attempts to auto load credentials from keyring."""

    def __init__(self, channel: "Channel", staging_creds: bool = False) -> None:
        login, password = _get_myqos_creds(staging_creds)
        if not (login is None or password is None):
            listen(channel, SendRequest, _gen_auth_injector(login, password))
        super().__init__(channel)


@asynccontextmanager
async def myqos_runtime(
    host: str, port: int = 443, local_debug: bool = False, staging_creds: bool = False
):
    async with Channel(host, port, ssl=(None if local_debug else True)) as channel:
        yield MyqosClient(channel, staging_creds)
