import asyncio
import sys
import traceback
from functools import wraps
from pathlib import Path
from typing import (
    AsyncContextManager,
    Dict,
    Optional,
    Sequence,
    cast,
)
import re

import click
from antlr4.error.Errors import ParseCancellationException  # type: ignore
from yachalk import chalk
from tierkreis import TierkreisGraph
from tierkreis.core.graphviz import tierkreis_to_graphviz
from tierkreis.core.types import (
    GraphType,
    StructType,
    TierkreisType,
    TierkreisTypeErrors,
)
from tierkreis.frontend import DockerRuntime, RuntimeClient, local_runtime
from tierkreis.frontend.myqos_client import myqos_runtime
from tierkreis.frontend.runtime_client import RuntimeSignature
from tierkreis.frontend.tksl import load_tksl_file

LOCAL_SERVER_PATH = Path(__file__).parent / "../../../../target/debug/tierkreis-server"
RUNTIME_LABELS = ["docker", "local", "myqos"]


def coro(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))

    return wrapper


async def _parse(source: Path, client: RuntimeClient) -> TierkreisGraph:
    try:
        return load_tksl_file(source, await client.get_signature())
    except ParseCancellationException as _parse_err:
        print(chalk.red(f"Parse error: {str(_parse_err)}"), file=sys.stderr)
        sys.exit(1)


async def _check_graph(
    source_path: Path, client_manager: AsyncContextManager[RuntimeClient]
) -> TierkreisGraph:
    async with client_manager as client:
        tkg = await _parse(source_path, client)
        try:
            tkg = await client.type_check_graph(tkg)
        except TierkreisTypeErrors as _errs:
            print(chalk.red(traceback.format_exc(0)), file=sys.stderr)
            sys.exit(1)
        return tkg


@click.group()
@click.pass_context
@click.option(
    "--runtime",
    "-R",
    type=click.Choice(RUNTIME_LABELS, case_sensitive=True),
    default="local",
)
@coro
async def cli(ctx: click.Context, runtime: str):
    ctx.ensure_object(dict)
    ctx.obj["runtime_label"] = runtime
    if runtime == "myqos":
        client_manager = myqos_runtime(
            "tierkreistrr595bx-pr.uksouth.cloudapp.azure.com"
            # "127.0.0.1", 8090, True
        )
    elif runtime == "docker":
        client_manager = DockerRuntime("cqc/tierkreis")
    else:
        assert LOCAL_SERVER_PATH.exists()
        client_manager = local_runtime(LOCAL_SERVER_PATH)
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
    source_path = Path(source)
    tkg = await _check_graph(source_path, ctx.obj["client_manager"])
    print(chalk.bold.green("Success: graph type check complete."))
    return tkg


@cli.command()
@click.argument("source", type=click.Path(exists=True))
@click.argument("view_path", type=click.Path(exists=False))
@click.option("--inline", is_flag=True)
@click.option("--check", "-C", is_flag=True)
@click.option("--recursive", is_flag=True)
@click.pass_context
@coro
async def view(
    ctx: click.Context,
    source: str,
    view_path: str,
    inline: bool,
    recursive: bool,
    check: bool,
):
    source_path = Path(source)
    if check:
        tkg = await _check_graph(source_path, ctx.obj["client_manager"])
    else:
        async with ctx.obj["client_manager"] as client:
            tkg = await _parse(source_path, client)
    if inline:
        tkg = tkg.inline_boxes(recursive=recursive)
    tkg.name = source_path.stem
    view_p = Path(view_path)
    ext = view_p.suffix
    tierkreis_to_graphviz(tkg).render(view_path[: -len(ext)], format=ext[1:])


@cli.command()
@click.argument("source", type=click.Path(exists=True))
@click.pass_context
@coro
async def run(ctx: click.Context, source: Path):
    async with ctx.obj["client_manager"] as client:
        client = cast(RuntimeClient, client)
        tkg = await _parse(source, client)
        try:
            outputs = await client.run_graph(tkg, {})
            print(
                "\n".join(
                    f"{chalk.bold.yellow(key)}: {val.to_tksl()}"
                    for key, val in outputs.items()
                )
            )
        except TierkreisTypeErrors as _errs:
            print(chalk.red(traceback.format_exc(0)), file=sys.stderr)


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
@click.option("--namespace", type=str)
@click.option("--function", type=str)
@coro
async def signature(
    ctx: click.Context, namespace: Optional[str], function: Optional[str]
):
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
