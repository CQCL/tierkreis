import os
import shutil
from pathlib import Path
from time import time_ns
from uuid import UUID

from tierkreis.controller.storage.pathstorage import PathStorageBase


class FileSystemBackend:
    def __init__(
        self,
        workflow_id: UUID,
        name: str | None = None,
        tierkreis_directory: Path = Path.home() / ".tierkreis" / "checkpoints",
        do_cleanup: bool = False,
    ) -> None:
        self.workflow_dir: Path = tierkreis_directory / str(workflow_id)
        self.logs_path = self.workflow_dir / "logs"
        self.name = name
        if do_cleanup:
            self._delete()

    def _read(self, path: Path) -> bytes:
        with open(path, "rb") as fh:
            return fh.read()

    def _write(self, path: Path, value: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb+") as fh:
            fh.write(value)

    def _delete(self) -> None:
        uid = os.getuid()
        workflow_id = self.workflow_dir.name
        tmp_dir = Path(f"/tmp/{uid}/tierkreis/archive/{workflow_id}/{time_ns()}")
        tmp_dir.mkdir(parents=True)
        if self._exists(self.workflow_dir):
            shutil.move(self.workflow_dir, tmp_dir)

    def _link(self, src: Path, dst: Path) -> None:
        dst.parent.mkdir(parents=True, exist_ok=True)
        os.link(src, dst)

    def _touch(self, path: Path, is_dir: bool = False) -> None:
        if is_dir:
            path.mkdir(parents=True, exist_ok=True)
            return

        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()

    def _exists(self, path: Path) -> bool:
        return path.exists()


class ControllerFileStorage(FileSystemBackend, PathStorageBase): ...
