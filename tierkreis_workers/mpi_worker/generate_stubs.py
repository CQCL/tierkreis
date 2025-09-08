# /// script
# requires-python = ">=3.12"
# dependencies = ["tierkreis"]
#
# [tool.uv.sources]
# tierkreis = { path = "../../tierkreis", editable = true }
# ///

import logging
from pathlib import Path
import shutil
import subprocess
from tierkreis.codegen import format_namespace, Namespace


def write_stubs(namespace: Namespace, stubs_path: Path) -> None:
    with open(stubs_path, "w+") as fh:
        fh.write(format_namespace(namespace))

    ruff_binary = shutil.which("ruff")
    if ruff_binary:
        subprocess.run([ruff_binary, "format", stubs_path])
        subprocess.run([ruff_binary, "check", "--fix", stubs_path])
    else:
        logging.warning("No ruff binary found. Stubs will contain raw codegen.")


if __name__ == "__main__":
    namespace = Namespace.from_spec_file(
        Path("./tierkreis_workers/mpi_worker/namespace.tsp")
    )
    write_stubs(namespace, Path("./tierkreis_workers/mpi_worker/stubs.py"))
