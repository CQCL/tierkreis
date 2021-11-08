from typing import Coroutine, Callable, Tuple, Optional
from contextlib import asynccontextmanager

import keyring

from grpclib.events import listen
from grpclib.events import SendRequest
from grpclib.client import Channel

from .runtime_client import RuntimeClient


def _get_myqos_creds(staging: bool = False) -> Tuple[Optional[str], Optional[str]]:
    keyring_service = "myqos-staging" if staging else "Myqos"
    login = keyring.get_password(keyring_service, "login")
    password = keyring.get_password(keyring_service, "password")
    return login, password


def _gen_auth_injector(login: str, pwd: str) -> Callable[["SendRequest"], Coroutine]:
    async def _inject_auth(event: SendRequest) -> None:
        event.metadata["token"] = login  # type: ignore
        event.metadata["key"] = pwd  # type: ignore

    return _inject_auth


class MyqosClient(RuntimeClient):
    """Runtime client for use with tierkreis hosted on mushroom.
    Attempts to auto load credentials from keyring."""

    def __init__(self, channel: "Channel") -> None:
        login, password = _get_myqos_creds()
        if not (login is None or password is None):
            listen(channel, SendRequest, _gen_auth_injector(login, password))
        super().__init__(channel)


@asynccontextmanager
async def myqos_runtime(host: str, port: int = 443):
    async with Channel(host, port, ssl=True) as channel:
        yield MyqosClient(channel)