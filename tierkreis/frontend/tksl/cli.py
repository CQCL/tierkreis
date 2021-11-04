import asyncio
import pprint
import traceback
from functools import wraps
from pathlib import Path
from typing import AsyncContextManager, Optional, TextIO
import tempfile

import click
from antlr4.error.Errors import ParseCancellationException  # type: ignore
from tierkreis import TierkreisGraph
from tierkreis.core.graphviz import tierkreis_to_graphviz
from tierkreis.core.types import TierkreisTypeErrors
from tierkreis.frontend import RuntimeClient, DockerRuntime, local_runtime
from tierkreis.frontend.tksl import parse_tksl
from tierkreis.frontend.myqos_client import myqos_runtime

LOCAL_SERVER_PATH = Path(__file__).parent / "../../../../target/debug/tierkreis-server"


def coro(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))

    return wrapper


async def _parse(source: TextIO, client: RuntimeClient) -> TierkreisGraph:
    try:
        return parse_tksl(source.read(), await client.get_signature())
    except ParseCancellationException as _parse_err:
        traceback.print_exc(0)
        exit()


@click.group()
@click.pass_context
@click.option(
    "--runtime",
    type=click.Choice(["docker", "local", "myqos"], case_sensitive=True),
    default="local",
)
@coro
async def cli(ctx: click.Context, runtime: str):
    ctx.ensure_object(dict)

    if runtime == "myqos":
        client_manager = myqos_runtime(
            "tierkreistrr595bx-pr.uksouth.cloudapp.azure.com"
        )
    elif runtime == "docker":
        client_manager = DockerRuntime("cqc/tierkreis")
    else:
        assert LOCAL_SERVER_PATH.exists()
        client_manager = local_runtime(LOCAL_SERVER_PATH)
    asyncio.get_event_loop()
    ctx.obj["client_manager"] = client_manager


async def _check_graph(
    source_path: Path, client_manager: AsyncContextManager[RuntimeClient]
) -> TierkreisGraph:
    async with client_manager as client:
        with open(source_path, "r") as f:
            tkg = await _parse(f, client)
        try:
            tkg = await client.type_check_graph(tkg)
        except TierkreisTypeErrors as _errs:
            traceback.print_exc(0)
            exit()
        return tkg


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
    # async with ctx.obj["client_manager"] as client:
    #     with open(source_path, "r") as f:
    #         tkg = await _parse(f, client)
    #     try:
    #         tkg = await client.type_check_graph(tkg)
    #     except TierkreisTypeErrors as _errs:
    #         traceback.print_exc(0)
    #         return

    with open(target_path, "wb") as f:
        f.write(bytes(tkg.to_proto()))


@cli.command()
@click.argument("source", type=click.Path(exists=True))
@click.option("--view", is_flag=True)
@click.pass_context
@coro
async def check(ctx: click.Context, source: str, view: bool) -> TierkreisGraph:
    source_path = Path(source)
    async with ctx.obj["client_manager"] as client:
        with open(source_path, "r") as f:
            tkg = await _parse(f, client)
        try:
            tkg = await client.type_check_graph(tkg)
        except TierkreisTypeErrors as _errs:
            traceback.print_exc(0)
            exit()
    if view:
        tkg.name = source_path.stem
        tierkreis_to_graphviz(tkg).view(tempfile.mktemp(".gv"))

    return tkg


@cli.command()
@click.argument("source", type=click.File("r"))
@click.pass_context
@coro
async def run(ctx: click.Context, source: TextIO):
    async with ctx.obj["client_manager"] as client:
        tkg = await _parse(source, client)
        try:
            pprint.pprint(await client.run_graph(tkg, {}))
        except TierkreisTypeErrors as _errs:
            traceback.print_exc(0)
