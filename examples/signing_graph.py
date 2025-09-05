from pathlib import Path
from uuid import UUID
from tierkreis.builder import GraphBuilder
from tierkreis.controller.executor.stdinout import StdInOut
from tierkreis.models import TKR, EmptyModel
from tierkreis.storage import FileStorage, read_outputs
from tierkreis.executor import MultipleExecutor, UvExecutor, ShellExecutor
from tierkreis import run_graph

from example_workers.auth_worker.stubs import sign, verify


def signing_graph():
    g = GraphBuilder(EmptyModel, TKR[bool])
    message = g.const("dummymessage")
    passphrase = g.const(b"dummypassphrase")

    key_pair = g.data.func(  # escape hatch into untyped builder
        "openssl_worker.genrsa",
        {"passphrase": passphrase.value_ref(), "numbits": g.const(4096).value_ref()},
    )
    private_key: TKR[bytes] = TKR(*key_pair("private_key"))  # unsafe cast
    public_key: TKR[bytes] = TKR(*key_pair("public_key"))  # unsafe cast

    signing_result = g.task(sign(private_key, passphrase, message)).hex_signature
    verification_result = g.task(verify(public_key, signing_result, message))
    g.outputs(verification_result)

    return g


def stdinout_graph():
    g = GraphBuilder(EmptyModel, TKR[str])
    message = g.const("dummymessage")
    passphrase = g.const(b"dummypassphrase")
    private_key = g.task("openssl_worker.genrsa", passphrase)
    signing_result = g.task(sign(private_key, passphrase, message)).hex_signature
    g.outputs(signing_result)
    return g


if __name__ == "__main__":
    storage = FileStorage(UUID(int=105))
    storage.clean_graph_files()

    registry_path = Path(__file__).parent / "example_workers"

    uv = UvExecutor(registry_path, storage.logs_path)
    shell = ShellExecutor(registry_path, storage.logs_path)
    executor = MultipleExecutor(uv, {"shell": shell}, {"openssl_worker": "shell"})

    run_graph(storage, executor, signing_graph().get_data(), {})
    is_verified = read_outputs(signing_graph().get_data(), storage)
    print(is_verified)
    assert is_verified

    storage.clean_graph_files()
    stdinout = StdInOut(registry_path, storage.logs_path)
    executor = MultipleExecutor(
        uv, {"stdinout": stdinout}, {"openssl_worker": "stdinout"}
    )
    run_graph(storage, executor, stdinout_graph().get_data(), {})
    out = read_outputs(stdinout_graph().get_data(), storage)
    print(out)
    assert False
