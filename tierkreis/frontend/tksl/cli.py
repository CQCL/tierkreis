import asyncio
import pprint
import traceback
from functools import wraps
from pathlib import Path
from typing import Optional, TextIO

import click
from antlr4.error.Errors import ParseCancellationException
from tierkreis import TierkreisGraph
from tierkreis.core.graphviz import tierkreis_to_graphviz
from tierkreis.core.types import TierkreisTypeErrors
from tierkreis.frontend import RuntimeClient, local_runtime, parse_tksl

LOCAL_SERVER_PATH = Path(__file__).parent / "../../../../target/debug/tierkreis-server"

assert LOCAL_SERVER_PATH.exists()


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
def cli():
    pass


@cli.command()
@click.argument("source", type=click.Path(exists=True))
@click.option("--target", type=click.Path(exists=False))
@click.option("--view", is_flag=True)
@coro
async def build(source: str, target: Optional[str], view: bool):
    source_path = Path(source)
    if target:
        target_path = Path(target)
    else:
        assert source_path.suffix == ".tksl"
        target_path = source_path.with_suffix(".bin")
    async with local_runtime(LOCAL_SERVER_PATH) as client:
        with open(source_path, "r") as f:
            tkg = await _parse(f, client)
        try:
            tkg = await client.type_check_graph(tkg)
        except TierkreisTypeErrors as errs:
            traceback.print_exc(0)
            exit()

        with open(target_path, "wb") as f:
            f.write(bytes(tkg.to_proto()))
    if view:
        tierkreis_to_graphviz(tkg).render(view=True)


@cli.command()
@click.argument("source", type=click.File("r"))
@coro
async def run(source: TextIO):
    async with local_runtime(LOCAL_SERVER_PATH) as client:
        tkg = await _parse(source, client)
        try:
            pprint.pprint(await client.run_graph(tkg, {}))
        except TierkreisTypeErrors as errs:
            traceback.print_exc(0)
            exit()
