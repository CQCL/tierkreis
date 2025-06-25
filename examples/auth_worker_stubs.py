"""Code generated from auth_worker namespace. Please do not edit."""

from typing import NamedTuple
from tierkreis.controller.data.core import TKRRef, Function, NodeIndex


class EncryptOutput(NamedTuple):
    ciphertext: TKRRef[str]
    time_taken: TKRRef[float]

    @staticmethod
    def from_nodeindex(n: NodeIndex) -> "EncryptOutput":
        return EncryptOutput(
            ciphertext=TKRRef[str](n, "ciphertext"),
            time_taken=TKRRef[float](n, "time_taken"),
        )


class encrypt(Function[EncryptOutput]):
    plaintext: TKRRef[str]
    work_factor: TKRRef[int]

    @staticmethod
    def out(idx: NodeIndex) -> EncryptOutput:
        return EncryptOutput.from_nodeindex(idx)

    @property
    def namespace(self) -> str:
        return "auth_worker"
