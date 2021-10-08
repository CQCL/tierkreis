from typing import Coroutine, Callable, TYPE_CHECKING, Tuple, Optional
import keyring
from grpclib.events import listen
from grpclib.events import SendRequest

from .runtime_client import RuntimeClient

if TYPE_CHECKING:
    from grpclib.client import Channel


def _get_myqos_creds() -> Tuple[Optional[str], Optional[str]]:
    keyring_service = "Myqos"
    # TODO DON'T COMMIT ME
    # keyring_service = "myqos-staging"
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
