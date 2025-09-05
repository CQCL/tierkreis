"""Code generated from slurm_mpi_worker namespace. Please do not edit."""

from typing import NamedTuple
from types import NoneType
from tierkreis.controller.data.models import TKR


class mpi_rank_info(NamedTuple):
    @staticmethod
    def out() -> type[TKR[str | NoneType]]:  # noqa: F821 # fmt: skip
        return TKR[str | NoneType]  # noqa: F821 # fmt: skip

    @property
    def namespace(self) -> str:
        return "slurm_mpi_worker"
