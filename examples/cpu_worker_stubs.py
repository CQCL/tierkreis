"""Code generated from cpu_worker namespace. Please do not edit."""

from typing import NamedTuple
from tierkreis.controller.data.core import TKRRef, Function, NodeIndex


class encryptOutput(NamedTuple):
    ciphertext: TKRRef[str]
    time_taken: TKRRef[float]

    @staticmethod
    def from_nodeindex(n: NodeIndex) -> "encryptOutput":
        return encryptOutput(
            ciphertext=TKRRef[str](n, "ciphertext"),
            time_taken=TKRRef[float](n, "time_taken"),
        )


class encrypt(Function[encryptOutput]):
    plaintext: TKRRef[str]
    work_factor: TKRRef[int]

    @staticmethod
    def out(idx: NodeIndex) -> encryptOutput:
        return encryptOutput.from_nodeindex(idx)

    @property
    def namespace(self) -> str:
        return "cpu_worker"
