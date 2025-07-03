import json
from pathlib import Path

from tierkreis.controller.data.location import WorkerCallArgs


class WorkerFileStorage:
    def __init__(
        self,
        tierkreis_dir: Path = Path.home() / ".tierkreis" / "checkpoints",
    ) -> None:
        self.tierkreis_dir = tierkreis_dir

    def read_call_args(self, path: Path) -> WorkerCallArgs:
        with open(path, "r") as fh:
            return WorkerCallArgs(**json.loads(fh.read()))

    def read_input(self, path: Path) -> bytes:
        with open(path, "rb") as fh:
            return fh.read()

    def write_output(self, path: Path, value: bytes) -> None:
        with open(path, "wb+") as fh:
            fh.write(value)
