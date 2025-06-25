"""Code generated from cpu_worker namspace. Please do not edit."""

from typing import NamedTuple
from tierkreis.controller.data.core import TKRRef, Function, NodeIndex


class encryptOutput(NamedTuple):
    time_taken: TKRRef[float]
    ciphertext: TKRRef[str]

    @staticmethod
    def from_nodeindex(n: NodeIndex) -> "encryptOutput":
        return encryptOutput(
            time_taken=TKRRef[float](n, "time_taken"),
            ciphertext=TKRRef[str](n, "ciphertext"),
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
