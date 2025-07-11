"""Code generated from auth_worker namespace. Please do not edit."""

# ruff: noqa: F821
from typing import NamedTuple
from tierkreis.controller.data.models import TKR


class EncryptionResult(NamedTuple):
    ciphertext: TKR[str]
    time_taken: TKR[float]


class encrypt(NamedTuple):
    plaintext: TKR[str]
    work_factor: TKR[int]

    @staticmethod
    def out() -> type[EncryptionResult]:
        return EncryptionResult

    @property
    def namespace(self) -> str:
        return "auth_worker"
