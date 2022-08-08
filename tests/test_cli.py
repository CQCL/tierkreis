import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from tierkreis.frontend import ServerRuntime


@pytest.mark.asyncio
def test_build_view(server_client: "ServerRuntime"):
    host, port = server_client.socket_address().split(":")
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


@pytest.mark.asyncio
def test_run_with_args(server_client: "ServerRuntime"):
    host, port = server_client.socket_address().split(":")
    nint_tksl = Path(__file__).parent.absolute() / "tksl_samples" / "nint_adder.tksl"
    command_header = ["tksl", "-r", host, "-p", port, "run", str(nint_tksl)]

    output = subprocess.check_output(command_header + ["array: [3, 5, 11], len: 2"])
    assert output.decode("utf-8").strip() == "out: 16"

    output = subprocess.check_output(command_header + ["array: [1, 3, 5, 11], len: 4"])
    assert output.decode("utf-8").strip() == "out: 20"

    output = subprocess.check_output(command_header + ["array: [], len: 0"])
    assert output.decode("utf-8").strip() == "out: 0"

    p = subprocess.run(command_header + ["array: []"], capture_output=True)
    assert p.returncode != 0
    assert "Failed to unify types" in p.stderr.decode("utf-8")
