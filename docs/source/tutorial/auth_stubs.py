"""Code generated from auth_worker namespace. Please do not edit."""

from typing import Literal, NamedTuple, Sequence, TypeVar, Generic, Protocol
from types import NoneType
from tierkreis.controller.data.models import TKR, OpaqueType
from tierkreis.controller.data.types import PType, Struct






class EncryptionResult(NamedTuple):
    ciphertext: TKR[str]  # noqa: F821 # fmt: skip
    time_taken: TKR[float]  # noqa: F821 # fmt: skip


class encrypt(NamedTuple):
    plaintext: TKR[str]  # noqa: F821 # fmt: skip
    work_factor: TKR[int]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[EncryptionResult]: # noqa: F821 # fmt: skip
        return EncryptionResult # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "auth_worker" 
    