from pathlib import Path
from uuid import UUID

from tierkreis.consts import PACKAGE_PATH
from tierkreis import run_graph
from tierkreis.controller.executor.multiple import MultipleExecutor
from tierkreis.storage import FileStorage, read_outputs
from tierkreis.executor import UvExecutor, ShellExecutor

from signing_graph import signing_graph


storage = FileStorage(
    UUID(int=108),
    do_cleanup=True,
    tierkreis_directory=Path.home() / ".tierkreis" / "checkpoints2",
)
uv = UvExecutor(PACKAGE_PATH / ".." / "examples" / "example_workers", storage.logs_path)
shell = ShellExecutor(
    PACKAGE_PATH / ".." / "examples" / "example_workers", storage.workflow_dir
)
executor = MultipleExecutor(uv, {"shell": shell}, {"openssl_worker": "shell"})

run_graph(storage, executor, signing_graph(), {}, polling_interval_seconds=0.1)
out = read_outputs(signing_graph(), storage)
print(out)
assert isinstance(out, bool)
