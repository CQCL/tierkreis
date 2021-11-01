from typing import Union
from pathlib import Path
import pytest

from tierkreis.frontend import RuntimeClient, parse_tksl


def _get_source(path: Union[str, Path]) -> str:
    with open(path) as f:
        return f.read()


@pytest.mark.asyncio
async def test_parse_sample(client: RuntimeClient) -> None:
    sig = await client.get_signature()

    tg = parse_tksl(
        _get_source(Path(__file__).parent / "tksl_samples/antlr_sample.tksl"), sig
    )
    tg = await client.type_check_graph(tg)
    print(tg)
