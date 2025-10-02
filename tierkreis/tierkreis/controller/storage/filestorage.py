import os
import shutil
from pathlib import Path
from time import time_ns
from uuid import UUID

from tierkreis.controller.storage.pathstorage import PathStorageBase, StatResult


class FileSystemBackend:
    def __init__(
        self,
        workflow_id: UUID,
        name: str | None = None,
        tierkreis_directory: Path = Path.home() / ".tierkreis" / "checkpoints",
        do_cleanup: bool = False,
    ) -> None:
        self.tkr_dir = tierkreis_directory
        self.workflow_id = workflow_id
        self.name = name
        if do_cleanup:
            self._delete()

    def _delete(self) -> None:
        uid = os.getuid()
        tmp_dir = Path(f"/tmp/{uid}/tierkreis/archive/{self.workflow_id}/{time_ns()}")
        tmp_dir.mkdir(parents=True)
        workflow_dir = self.tkr_dir / str(self.workflow_id)
        if self._exists(workflow_dir):
            shutil.move(workflow_dir, tmp_dir)

    def _exists(self, path: Path) -> bool:
        return path.exists()

    def _list_output_paths(self, output_dir: Path) -> list[Path]:
        return [x for x in output_dir.iterdir() if x.is_file()]

    def _link(self, src: Path, dst: Path) -> None:
        dst.parent.mkdir(parents=True, exist_ok=True)
        os.link(src, dst)

    def _read(self, path: Path) -> bytes:
        with open(path, "rb") as fh:
            return fh.read()

    def _touch(self, path: Path, is_dir: bool = False) -> None:
        if is_dir:
            path.mkdir(parents=True, exist_ok=True)
            return

        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()

    def _stat(self, path: Path) -> StatResult:
        return StatResult(path.stat().st_mtime)

    def _write(self, path: Path, value: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb+") as fh:
            fh.write(value)


class ControllerFileStorage(FileSystemBackend, PathStorageBase): ...
