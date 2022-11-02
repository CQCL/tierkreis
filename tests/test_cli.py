import subprocess
import tempfile
from typing import TYPE_CHECKING

import pytest

import tierkreis.core.protos.tierkreis.graph as pg
from tierkreis.core.values import IntValue, StructValue, VecValue

from .utils import nint_adder

if TYPE_CHECKING:
    from tierkreis.client import ServerRuntime


@pytest.mark.asyncio
def test_signature(server_client: "ServerRuntime"):
    host, port = server_client.socket_address().split(":")
    command = ["tksl", "-r", host, "-p", port, "signature"]
    p = subprocess.run(command, capture_output=True)
    print(p.stderr)
    assert p.returncode == 0


@pytest.mark.asyncio
def test_view(server_client: "ServerRuntime"):
    host, port = server_client.socket_address().split(":")
    with tempfile.TemporaryDirectory() as tmpdirname:
        nint_adder_file_2 = tmpdirname + "/nint_adder_2.bin"
        with open(nint_adder_file_2, "wb") as f:
            f.write(bytes(nint_adder(2).to_proto()))
        command = [
            "tksl",
            "-r",
            host,
            "-p",
            port,
            "view",
            str(nint_adder_file_2),
            tmpdirname + "test_tierkreis_proto.pdf",
        ]
        assert subprocess.call(command) == 0


@pytest.mark.asyncio
def test_run_with_args(server_client: "ServerRuntime"):
    host, port = server_client.socket_address().split(":")
    command_header = ["tksl", "-r", host, "-p", port, "run"]
    with tempfile.TemporaryDirectory() as tmpdirname:
        nint_adder_file_2 = tmpdirname + "/nint_adder_2.bin"
        with open(nint_adder_file_2, "wb") as f:
            f.write(bytes(nint_adder(2).to_proto()))
        v: StructValue = StructValue(
            {
                "array": VecValue(values=[IntValue(3), IntValue(5), IntValue(11)]),
            }
        )
        fname = tmpdirname + "/test1.bin"
        with open(fname, "wb") as f:
            f.write(bytes(pg.StructValue(map=v.to_proto_dict())))
        output = subprocess.check_output(command_header + [nint_adder_file_2, fname])
        assert output.decode("utf-8").strip() == "out: 16"

        nint_adder_file_4 = tmpdirname + "/nint_adder_4.bin"
        with open(nint_adder_file_4, "wb") as f:
            f.write(bytes(nint_adder(4).to_proto()))
        v = StructValue(
            {
                "array": VecValue(
                    values=[IntValue(1), IntValue(3), IntValue(5), IntValue(11)]
                ),
            }
        )
        fname = tmpdirname + "/test2.bin"
        with open(fname, "wb") as f:
            f.write(bytes(pg.StructValue(map=v.to_proto_dict())))
        output = subprocess.check_output(command_header + [nint_adder_file_4, fname])
        assert output.decode("utf-8").strip() == "out: 20"

        v = StructValue({"array_wrong_name": VecValue(values=[])})
        fname = tmpdirname + "/test4.bin"
        with open(fname, "wb") as f:
            f.write(bytes(pg.StructValue(map=v.to_proto_dict())))
        p = subprocess.run(
            command_header + [nint_adder_file_2, fname], capture_output=True
        )
        assert p.returncode != 0
        assert "Expected type" in p.stderr.decode("utf-8")
