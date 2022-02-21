import asyncio
import sys
import traceback
from functools import wraps
from pathlib import Path
from typing import (
    AsyncContextManager,
    Dict,
    List,
    Optional,
    Sequence,
    cast,
)
import re
from signal import SIGINT, SIGTERM

import click
from antlr4.error.Errors import ParseCancellationException  # type: ignore
from yachalk import chalk
from tierkreis import TierkreisGraph
from tierkreis.core.values import TierkreisValue
from tierkreis.core.graphviz import tierkreis_to_graphviz
from tierkreis.core.types import (
    GraphType,
    StructType,
    TierkreisType,
    TierkreisTypeErrors,
)
from tierkreis.frontend import (
    RuntimeClient,
    local_runtime,
)
from tierkreis.frontend.docker_manager import docker_runtime
from tierkreis.frontend.myqos_client import myqos_runtime
from tierkreis.frontend.runtime_client import RuntimeSignature, TaskHandle
from tierkreis.frontend.tksl import load_tksl_file

LOCAL_SERVER_PATH = Path(__file__).parent / "../../../../target/debug/tierkreis-server"
RUNTIME_LABELS = ["docker", "local", "myqos"]


def coro(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))

    return wrapper


async def _parse(source: Path, client: RuntimeClient, **kwargs) -> TierkreisGraph:
    try:
        return load_tksl_file(source, signature=await client.get_signature(), **kwargs)
    except ParseCancellationException as _parse_err:
        print(chalk.red(f"Parse error: {str(_parse_err)}"), file=sys.stderr)
        sys.exit(1)


async def _check_graph(
    source_path: Path, client_manager: AsyncContextManager[RuntimeClient], **kwargs
) -> TierkreisGraph:
    async with client_manager as client:
        tkg = await _parse(source_path, client, **kwargs)
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
def local(executable: Path, worker: List[str], port: int, remote_worker: Optional[str]):
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
def docker(
    image: str,
    worker: List[str],
    docker_worker: List[str],
    port: int,
    remote_worker: Optional[str],
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
        )
    )


@click.group()
@click.pass_context
@click.option(
    "--runtime",
    "-r",
    default="tierkreis.myqos.com",
    help="Choose runtime, default=myqos",
)
@click.option(
    "--port",
    "-p",
    help="Runtime port, default=8090 if runtime is localhost, else 443",
)
@coro
async def cli(ctx: click.Context, runtime: str, port: Optional[int]):
    local = runtime == "localhost"
    if port is None:
        port = 8090 if local else 443
    ctx.ensure_object(dict)
    ctx.obj["runtime_label"] = runtime
    client_manager = myqos_runtime(runtime, port, local_debug=local)
    asyncio.get_event_loop()
    ctx.obj["client_manager"] = client_manager


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
    tkg = await _check_graph(source_path, ctx.obj["client_manager"])
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
            source_path, ctx.obj["client_manager"], function_name=function
        )
    else:
        async with ctx.obj["client_manager"] as client:
            tkg = await _parse(source_path, client, function_name=function)

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
@click.pass_context
@coro
async def run(ctx: click.Context, source: Path):
    """Run SOURCE on runtime and output to console."""
    async with ctx.obj["client_manager"] as client:
        client = cast(RuntimeClient, client)
        tkg = await _parse(source, client)
        try:
            outputs = await client.run_graph(tkg, {})
            _print_outputs(outputs)
        except TierkreisTypeErrors as _errs:
            print(chalk.red(traceback.format_exc(0)), file=sys.stderr)


@cli.command()
@click.argument("source", type=click.Path(exists=True))
@click.pass_context
@coro
async def submit(ctx: click.Context, source: Path):
    """Submit SOURCE to runtime and print task id to console."""
    async with ctx.obj["client_manager"] as client:
        client = cast(RuntimeClient, client)
        tkg = await _parse(source, client)
        try:
            task_handle = await client.start_task(tkg, {})
            print(chalk.bold.yellow("Task id:"), task_handle.task_id)
        except TierkreisTypeErrors as _errs:
            _print_typeerrs(traceback.format_exc(0))


@cli.command()
@click.argument("task_id")
@click.pass_context
@coro
async def retrieve(ctx: click.Context, task_id: str):
    """Retrive outputs of submitted graph from runtime, using TASK_ID."""
    async with ctx.obj["client_manager"] as client:
        client = cast(RuntimeClient, client)
        outputs = await client.await_task(TaskHandle(task_id))
        _print_outputs(outputs)


@cli.command()
@click.argument("task_id")
@click.pass_context
@coro
async def delete(ctx: click.Context, task_id: str):
    """Delete task by TASK_ID."""
    async with ctx.obj["client_manager"] as client:
        client = cast(RuntimeClient, client)
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
        client = cast(RuntimeClient, client)
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


def _arg_str(args: Dict[str, TierkreisType], order: Sequence[str]) -> str:
    return ", ".join(f"{chalk.yellow(port)}: {str(args[port])}" for port in order)


PORT_RE = re.compile(r"([\w]+):")


def _print_namespace(sig: RuntimeSignature, namespace: str, function: Optional[str]):
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
        func = names_dict[name]
        graph_type = cast(GraphType, func.type_scheme.body)
        irest = graph_type.inputs.rest
        orest = graph_type.outputs.rest
        irest = f", {chalk.yellow('#')}: {irest}" if irest else ""
        orest = f", {chalk.yellow('#')}: {orest}" if orest else ""
        print(
            f"{chalk.bold.blue(name)}"
            f"({_arg_str(graph_type.inputs.content, func.input_order)}{irest})"
            f" -> ({_arg_str(graph_type.outputs.content, func.output_order)}{orest})"
        )
        if func.docs:
            print(chalk.green(func.docs))
        print()


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
        client = cast(RuntimeClient, client)
        label = ctx.obj["runtime_label"]
        print(chalk.bold(f"Runtime: {label}"))
        print()
        sig = await client.get_signature()
        namespaces = [namespace] if namespace else list(sig.keys())

        for namespace in namespaces:
            _print_namespace(sig, namespace, function)
            print()
