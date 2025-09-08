"""Code generated from MPIWorker namespace. Please do not edit."""

from typing import NamedTuple
from tierkreis.controller.data.models import TKR


class double(NamedTuple):
    value: TKR[list[int]]  # noqa: F821 # fmt: skip

    @staticmethod
    def out() -> type[TKR[list[int]]]:  # noqa: F821 # fmt: skip
        return TKR[list[int]]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "MPIWorker"
