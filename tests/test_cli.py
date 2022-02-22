from typing import TYPE_CHECKING
import subprocess
import tempfile
from pathlib import Path

import pytest

if TYPE_CHECKING:
    from tierkreis.frontend import RuntimeClient


@pytest.mark.asyncio
def test_build_view(client: "RuntimeClient"):
    host, port = client.socket_address().split(":")
    command_header = ["tksl", "-r", host, "-p", port]
    with tempfile.TemporaryDirectory() as tmpdirname:
        binfile = tmpdirname + "/test_tierkreis_proto.bin"
        visfile = tmpdirname + "/test_tierkreis_proto.pdf"
        assert (
            subprocess.call(
                command_header
                + [
                    "build",
                    str(Path(__file__).parent / "tksl_samples/nint_adder.tksl"),
                    "--target",
                    binfile,
                ]
            )
            == 0
        )

        assert (
            subprocess.call(
                command_header
                + [
                    "--proto",
                    "view",
                    binfile,
                    visfile,
                ]
            )
            == 0
        )
