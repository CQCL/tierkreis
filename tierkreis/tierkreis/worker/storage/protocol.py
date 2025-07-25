from pathlib import Path
from typing import Protocol

from tierkreis.controller.data.location import WorkerCallArgs


class WorkerStorage(Protocol):
    def read_call_args(self, path: Path) -> WorkerCallArgs: ...
    def read_input(self, path: Path) -> bytes: ...
    def write_output(self, path: Path, value: bytes) -> None: ...
