import asyncio
import re
import sys
import traceback
from contextlib import asynccontextmanager
from functools import wraps
from pathlib import Path
from signal import SIGINT, SIGTERM
from typing import TYPE_CHECKING, AsyncContextManager, Dict, List, Optional, cast

import click
from grpclib.client import Channel
from yachalk import chalk

import tierkreis.core.protos.tierkreis.v1alpha1.graph as pg
from tierkreis import TierkreisGraph
from tierkreis.builder import _func_sig
from tierkreis.client import ServerRuntime
from tierkreis.core.graphviz import tierkreis_to_graphviz
from tierkreis.core.protos.tierkreis.v1alpha1.graph import Graph as ProtoGraph
from tierkreis.core.signature import Signature
from tierkreis.core.type_errors import TierkreisTypeErrors
from tierkreis.core.types import StructType
from tierkreis.core.values import StructValue, TierkreisValue

if TYPE_CHECKING:
    from tierkreis.core.function import FunctionDeclaration


@asynccontextmanager
async def server_manager(host: str, port: int = 443):
    async with Channel(host, port) as channel:
        yield ServerRuntime(channel)


def coro(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))

    return wrapper


def _inputs(proto_file: str, py_source: str) -> Dict[str, TierkreisValue]:
    if proto_file == "":
        return (
            {}
            if py_source == ""
            else {k: TierkreisValue.from_python(v) for k, v in eval(py_source).items()}
        )
    if py_source != "":
        raise ValueError("Cannot provide both inputs and --py-inputs")
    path = Path(proto_file)
    with open(path, "rb") as f:
        v: StructValue = StructValue.from_proto(pg.StructValue().parse(f.read()))
        return v.values


async def _parse(source: Path) -> TierkreisGraph:
    with open(source, "rb") as f:
        return TierkreisGraph.from_proto(ProtoGraph().parse(f.read()))


async def _check_graph(
    source_path: Path,
    client_manager: AsyncContextManager[ServerRuntime],
) -> TierkreisGraph:
    async with client_manager as client:
        tkg = await _parse(source_path)
        try:
            tkg = await client.type_check_graph(tkg)
        except TierkreisTypeErrors:
            _print_typeerrs(traceback.format_exc(0))
            sys.exit(1)
        return tkg


async def main_coro(manager: AsyncContextManager):
    async with manager as runtime:
        try:
            print(runtime.socket_address(), flush=True)
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
@click.pass_context
@click.option(
    "--runtime",
    "-r",
    default="localhost",
    help="Choose runtime, default=localhost",
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
    client_manager = server_manager(runtime, port)
    asyncio.get_event_loop()
    ctx.obj["client_manager"] = client_manager


@cli.command()
@click.argument("proto", type=click.Path(exists=True))
@click.pass_context
@coro
async def check(ctx: click.Context, proto: str) -> TierkreisGraph:
    """Type check PROTO binary file against runtime signature."""
    source_path = Path(proto)
    tkg = await _check_graph(source_path, ctx.obj["client_manager"])
    print(chalk.bold.green("Success: graph type check complete."))
    return tkg


@cli.command()
@click.argument("proto", type=click.Path(exists=True))
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
@click.pass_context
@coro
async def view(
    ctx: click.Context,
    proto: str,
    view_path: str,
    check: bool,
    unbox_level: int,
):
    """Visualise PROTO binary as graph and output to VIEW_PATH."""
    source_path = Path(proto)
    if check:
        tkg = await _check_graph(
            source_path,
            ctx.obj["client_manager"],
        )
    else:
        tkg = await _parse(source_path)

    tkg.name = source_path.stem
    view_p = Path(view_path)
    ext = view_p.suffix
    tierkreis_to_graphviz(tkg, unbox_level=unbox_level).render(
        view_path[: -len(ext)], format=ext[1:]
    )


def _print_outputs(outputs: dict[str, TierkreisValue]):
    print(
        "\n".join(
            f"{chalk.bold.yellow(key)}: {val.viz_str()}" for key, val in outputs.items()
        )
    )


def _print_typeerrs(errs: str):
    print(chalk.red(errs), file=sys.stderr)


@cli.command()
@click.argument("proto", type=click.Path(exists=True))
@click.argument("inputs", default="")
@click.option("-p", "--py-inputs", default="")
@click.pass_context
@coro
async def run(ctx: click.Context, proto: Path, inputs: str, py_inputs: str):
    """Run PROTO binary on runtime with optional INPUTS and output to console."""
    async with ctx.obj["client_manager"] as client:
        client = cast(ServerRuntime, client)
        tkg = await _parse(proto)
        input_dict = _inputs(inputs, py_inputs)
        try:
            outputs = await client.run_graph(tkg, **input_dict)
            _print_outputs(outputs)
        except TierkreisTypeErrors:
            _print_typeerrs(traceback.format_exc(0))
            sys.exit(1)


PORT_RE = re.compile(r"([\w]+):")


def _print_namespace(sig: Signature, namespace: List[str], function: Optional[str]):
    namespace_str = "::".join(namespace)
    root = "_root"

    print(chalk.bold(f"Namespace: {root if namespace == [] else namespace_str}"))
    print()
    print(chalk.bold("Aliases and Struct definitions"))

    for alias, type_scheme in sig.aliases.items():
        prefix = f"{namespace_str}::"
        if not alias.startswith(prefix):
            continue
        alias = alias[len(prefix) :]
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
    print(chalk.bold("Functions"))

    names_dict = sig.root.get(namespace).functions
    func_names = [function] if function else list(names_dict.keys())
    for name in sorted(func_names):
        _print_func(name, names_dict[name])
        print()


def _print_func(name: str, func: "FunctionDeclaration"):
    print(_func_sig(name, func))
    if func.description:
        print(chalk.green(func.description))


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
        namespaces: list[list[str]] = (
            [namespace.split("::")] if namespace else sig.root.all_namespaces()
        )

        for ns in namespaces:
            _print_namespace(sig, ns, function)
            print()
