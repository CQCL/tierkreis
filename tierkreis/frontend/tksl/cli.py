import asyncio
import re
import sys
import traceback
from functools import wraps
from pathlib import Path
from signal import SIGINT, SIGTERM
from typing import TYPE_CHECKING, AsyncContextManager, Dict, List, Optional, cast

import click
from antlr4.error.Errors import ParseCancellationException  # type: ignore
from yachalk import chalk

from tierkreis import TierkreisGraph
from tierkreis.core.graphviz import tierkreis_to_graphviz
from tierkreis.core.protos.tierkreis.graph import Graph as ProtoGraph
from tierkreis.core.types import StructType, TierkreisTypeErrors
from tierkreis.core.values import StructValue, TierkreisValue
from tierkreis.frontend import ServerRuntime, local_runtime
from tierkreis.frontend.builder import _func_sig
from tierkreis.frontend.docker_manager import docker_runtime
from tierkreis.frontend.myqos_client import myqos_runtime
from tierkreis.frontend.runtime_client import RuntimeSignature, TaskHandle

from . import load_tksl_file
from .parse_tksl import parse_struct_fields

if TYPE_CHECKING:
    from tierkreis.core.function import TierkreisFunction

LOCAL_SERVER_PATH = Path(__file__).parent / "../../../../target/debug/tierkreis-server"
RUNTIME_LABELS = ["docker", "local", "myqos"]


def coro(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))

    return wrapper


def _inputs(source: str) -> Dict[str, TierkreisValue]:
    source = source.strip()
    if source == "":
        return {}
    try:
        v: StructValue = parse_struct_fields(source)
        return v.values
    except ParseCancellationException as _parse_err:
        print(chalk.red(f"Parse error in inputs: {_parse_err}"), file=sys.stderr)
        sys.exit(1)


async def _parse(
    source: Path, client: ServerRuntime, proto=False, **kwargs
) -> TierkreisGraph:
    if proto:
        if source.suffix == ".tksl":
            print(
                chalk.red(
                    "Warning: The source file ends in"
                    " .tksl but the proto flag is specified."
                    " Check you intend the input to be parsed as protobuf binary."
                )
            )
        with open(source, "rb") as f:
            return TierkreisGraph.from_proto(ProtoGraph().parse(f.read()))
    try:
        return load_tksl_file(source, signature=await client.get_signature(), **kwargs)
    except ParseCancellationException as _parse_err:
        print(chalk.red(f"Parse error: {str(_parse_err)}"), file=sys.stderr)
        sys.exit(1)


async def _check_graph(
    source_path: Path,
    client_manager: AsyncContextManager[ServerRuntime],
    proto=False,
    **kwargs,
) -> TierkreisGraph:
    async with client_manager as client:
        tkg = await _parse(source_path, client, proto=proto, **kwargs)
        try:
            tkg = await client.type_check_graph(tkg)
        except TierkreisTypeErrors as _errs:
            _print_typeerrs(traceback.format_exc(0))
            sys.exit(1)
        return tkg


async def main_coro(manager: AsyncContextManager):
    async with manager as runtime:
        try:
            print(runtime.socket_address())
            await asyncio.sleep(10000000000000)
        except asyncio.CancelledError:
            print("\nShutting Down")


def run_with_signals(manager: AsyncContextManager):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    main_task = loop.create_task(main_coro(manager))
    for signal in [SIGINT, SIGTERM]:
        loop.add_signal_handler(signal, main_task.cancel)
    try:
        loop.run_until_complete(main_task)
    finally:
        loop.close()


@click.group()
def start():
    """Start a tierkreis server on local host and print the address as
    "localhost:<port>".
    This can be passed to the tksl command, e.g.

    >> tksl -r localhost -p 8090 signature

    Start a local server binary:
    >> tksl-start local

    Start a local server from docker image:
    >> tksl-start docker

    See documentation of individual commands for more options.
    """


@start.command()
@click.argument("executable", type=click.Path(exists=True), default=LOCAL_SERVER_PATH)
@click.option("--worker", "-w", multiple=True, default=[])
@click.option("--port", "-p", default=8090)
@click.option("--remote-worker")
@click.option("--server-logs", "-s", is_flag=True, default=False)
def local(
    executable: Path,
    worker: List[str],
    port: int,
    remote_worker: Optional[str],
    server_logs: bool,
):
    """Start a local server with EXECUTABLE, on PORT, connected to local WORKERS
    and REMOTE_WORKER URI

    e.g.
    >> tksl-start local ../target/debug/tierkreis-server -w
       ../workers/pytket_worker --remote-worker http://localhost:8050"""
    run_with_signals(
        local_runtime(
            executable,
            workers=list(map(Path, worker)),
            myqos_worker=remote_worker,
            grpc_port=port,
            show_output=server_logs,
        )
    )


@start.command()
@click.argument("image", default="cqcregistry.azurecr.io/cqc/tierkreis:latest")
@click.option("--worker", "-w", multiple=True, default=[])
@click.option(
    "--docker-worker",
    "-d",
    multiple=True,
    default=[],
    help="worker in image in form image:path",
)
@click.option("--port", "-p", default=8090)
@click.option("--remote-worker")
@click.option("--server-logs", "-s", is_flag=True, default=False)
def docker(
    image: str,
    worker: List[str],
    docker_worker: List[str],
    port: int,
    remote_worker: Optional[str],
    server_logs: bool,
):
    """Start a local server with IMAGE, on PORT, connected to local WORKERS,
    DOCKER_WORKERs in images and REMOTE_WORKER URI

    e.g.
    >> tksl-start docker cqc/tierkreis
     -d cqc/tierkreis-workers:/root/workers/pytket_worker
     -d cqc/tierkreis-workers:/root/workers/qermit_worker
     -w ../workers/myqos_worker
     --remote-worker http://localhost:8050"""

    image_worker_gen = (worker_str.split(":", 2) for worker_str in docker_worker)
    image_workers = [(img, pth) for img, pth in image_worker_gen]
    run_with_signals(
        docker_runtime(
            image,
            grpc_port=port,
            worker_images=image_workers,
            host_workers=list(map(Path, worker)),
            myqos_worker=remote_worker,
            show_output=server_logs,
        )
    )


@click.group()
@click.pass_context
@click.option(
    "--runtime",
    "-r",
    default="tierkreis.myqos.com",
    help="Choose runtime, default=tierkreis.myqos.com",
)
@click.option(
    "--port",
    "-p",
    help="Runtime port, default=8090 if runtime is localhost, else 443",
)
@click.option(
    "--proto",
    help="Provide a protobuf binary instead of tksl source.",
    is_flag=True,
)
@coro
async def cli(ctx: click.Context, runtime: str, port: Optional[int], proto: bool):
    local = runtime == "localhost"
    if port is None:
        port = 8090 if local else 443
    ctx.ensure_object(dict)
    ctx.obj["runtime_label"] = runtime
    client_manager = myqos_runtime(runtime, port, local_debug=local)
    asyncio.get_event_loop()
    ctx.obj["client_manager"] = client_manager
    ctx.obj["proto"] = proto


@cli.command()
@click.argument("source", type=click.Path(exists=True))
@click.option(
    "--target",
    type=click.Path(exists=False),
    help="target file to write protobuf binary to.",
)
@click.pass_context
@coro
async def build(ctx: click.Context, source: str, target: Optional[str]):
    """Build protobuf binary from tksl SOURCE and write to TARGET"""
    if ctx.obj["proto"]:
        raise RuntimeError(
            "Protobuf binary source is invalid input to build command."
            + "Check --proto flag."
        )
    source_path = Path(source)
    if target:
        target_path = Path(target)
    else:
        assert source_path.suffix == ".tksl"
        target_path = source_path.with_suffix(".bin")
    tkg = await _check_graph(source_path, ctx.obj["client_manager"])

    with open(target_path, "wb") as f:
        f.write(bytes(tkg.to_proto()))


@cli.command()
@click.argument("source", type=click.Path(exists=True))
@click.pass_context
@coro
async def check(ctx: click.Context, source: str) -> TierkreisGraph:
    """Type check tksl SOURCE  file against runtime signature."""
    source_path = Path(source)
    tkg = await _check_graph(
        source_path, ctx.obj["client_manager"], proto=ctx.obj["proto"]
    )
    print(chalk.bold.green("Success: graph type check complete."))
    return tkg


@cli.command()
@click.argument("source", type=click.Path(exists=True))
@click.argument(
    "view_path",
    type=click.Path(exists=False),
)
@click.option("--check", "-C", is_flag=True, help="Type check and annotate graph.")
@click.option(
    "--unbox-level",
    default=0,
    help="Nesting level to which boxes and thunks should be unthunked, default=0.",
)
@click.option(
    "--function",
    default="main",
    help="The name of the graph to visualise, default is main",
)
@click.pass_context
@coro
async def view(
    ctx: click.Context,
    source: str,
    view_path: str,
    check: bool,
    unbox_level: int,
    function: str,
):
    """Visualise tksl SOURCE as tksl graph and output to VIEW_PATH."""
    source_path = Path(source)
    if check:
        tkg = await _check_graph(
            source_path,
            ctx.obj["client_manager"],
            proto=ctx.obj["proto"],
            function_name=function,
        )
    else:
        async with ctx.obj["client_manager"] as client:
            tkg = await _parse(
                source_path, client, proto=ctx.obj["proto"], function_name=function
            )

    tkg.name = source_path.stem
    view_p = Path(view_path)
    ext = view_p.suffix
    tierkreis_to_graphviz(tkg, unbox_level=unbox_level).render(
        view_path[: -len(ext)], format=ext[1:]
    )


def _print_outputs(outputs: dict[str, TierkreisValue]):
    print(
        "\n".join(
            f"{chalk.bold.yellow(key)}: {val.to_tksl()}" for key, val in outputs.items()
        )
    )


def _print_typeerrs(errs: str):
    print(chalk.red(errs), file=sys.stderr)


@cli.command()
@click.argument("source", type=click.Path(exists=True))
@click.argument("inputs", default="")
@click.pass_context
@coro
async def run(ctx: click.Context, source: Path, inputs: str):
    """Run SOURCE on runtime with optional INPUTS and output to console."""
    async with ctx.obj["client_manager"] as client:
        client = cast(ServerRuntime, client)
        tkg = await _parse(source, client)
        py_inputs = _inputs(inputs)
        try:
            outputs = await client.run_graph(tkg, **py_inputs)
            _print_outputs(outputs)
        except TierkreisTypeErrors as _errs:
            _print_typeerrs(traceback.format_exc(0))
            sys.exit(1)


@cli.command()
@click.argument("source", type=click.Path(exists=True))
@click.argument("inputs", default="")
@click.pass_context
@coro
async def submit(ctx: click.Context, source: Path, inputs: str):
    """Submit SOURCE and optional INPUTS to runtime and print task id to console."""
    async with ctx.obj["client_manager"] as client:
        client = cast(ServerRuntime, client)
        tkg = await _parse(source, client)
        py_inputs = _inputs(inputs)
        try:
            task_handle = await client.start_task(tkg, py_inputs)
            print(chalk.bold.yellow("Task id:"), task_handle.task_id)
        except TierkreisTypeErrors as _errs:
            _print_typeerrs(traceback.format_exc(0))
            sys.exit(1)


@cli.command()
@click.argument("task_id")
@click.pass_context
@coro
async def retrieve(ctx: click.Context, task_id: str):
    """Retrive outputs of submitted graph from runtime, using TASK_ID."""
    async with ctx.obj["client_manager"] as client:
        client = cast(ServerRuntime, client)
        outputs = await client.await_task(TaskHandle(task_id))
        _print_outputs(outputs)


@cli.command()
@click.argument("task_id")
@click.pass_context
@coro
async def delete(ctx: click.Context, task_id: str):
    """Delete task by TASK_ID."""
    async with ctx.obj["client_manager"] as client:
        client = cast(ServerRuntime, client)
        await client.delete_task(TaskHandle(task_id))
        print(f"Task {task_id} deleted")


@cli.command()
@click.option(
    "--task", default=None, type=click.STRING, help="Task id to report status for"
)
@click.pass_context
@coro
async def status(ctx: click.Context, task: Optional[str]):
    """Check status of tasks."""
    async with ctx.obj["client_manager"] as client:
        client = cast(ServerRuntime, client)
        task_statuses = await client.list_tasks()

        handles = [TaskHandle(task)] if task else list(task_statuses.keys())
        try:
            statuses = [task_statuses[handle] for handle in handles]
        except KeyError:
            print(chalk.red(f"Task with id {task} not found on runtime."))
            sys.exit(1)
        handle_ids = [handle.task_id for handle in handles]
        id_width = len(handle_ids[0])
        cell_format = "{:<{width}}"
        print(
            f"{chalk.bold(cell_format.format('Task ID', width=id_width))}"
            f"  {chalk.bold('Status')}"
        )
        print()
        for handle_id, status in zip(handle_ids, statuses):
            print(
                f"{cell_format.format(handle_id, width=id_width)}"
                f"  {status or 'unknown'}"
            )


PORT_RE = re.compile(r"([\w]+):")


def print_namespace(sig: RuntimeSignature, namespace: str, function: Optional[str]):
    print(chalk.bold(f"Namespace: {namespace}"))
    print()
    print(chalk.bold(f"Aliases and Struct definitions"))

    for alias, type_scheme in sig[namespace].aliases.items():
        type_ = type_scheme.body
        if isinstance(type_, StructType):
            alias_string = type_.anon_name()
            alias_string = PORT_RE.sub(
                lambda match: chalk.yellow(match.group()), alias_string
            )
        else:
            alias_string = str(type_)
        print(f"{chalk.bold.magenta(alias)} = {alias_string}\n")

    print()
    print(chalk.bold(f"Functions"))

    names_dict = sig[namespace].functions
    func_names = [function] if function else list(names_dict.keys())
    for name in sorted(func_names):
        _print_func(name, names_dict[name])
        print()


def _print_func(name: str, func: "TierkreisFunction"):
    print(_func_sig(name, func))
    if func.docs:
        print(chalk.green(func.docs))


@cli.command()
@click.pass_context
@click.option("--namespace", type=str, help="Show only signatures of this namespace.")
@click.option(
    "--function", type=str, help="Show only the signature of a particular function."
)
@coro
async def signature(
    ctx: click.Context, namespace: Optional[str], function: Optional[str]
):
    """Check signature of available namespaces and functions on runtime."""
    async with ctx.obj["client_manager"] as client:
        client = cast(ServerRuntime, client)
        label = ctx.obj["runtime_label"]
        print(chalk.bold(f"Runtime: {label}"))
        print()
        sig = await client.get_signature()
        namespaces = [namespace] if namespace else list(sig.keys())

        for namespace in namespaces:
            print_namespace(sig, namespace, function)
            print()
