import asyncio

from tierkreis import TierkreisGraph
from tierkreis.client.myqos_client import myqos_runtime


async def main():

    tg = TierkreisGraph()
    unpack = tg.add_func("builtin/unpack_pair", pair=(2, "asdf"))
    tg.set_outputs(first=unpack["first"], second=unpack["second"])

    async with myqos_runtime("tierkreis.myqos.com") as client:
        print(await client.run_graph(tg, {}))


asyncio.run(main())
