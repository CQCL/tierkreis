import pytest
import json

from tierkreis.pyruntime import PyRuntime

from hugr import Hugr
from hugr._serialization.serial_hugr import SerialHugr
from hugr.val import TRUE, FALSE, Tuple
from hugr.std.int import IntVal


@pytest.mark.asyncio
async def test_factorial():
    with open("/Users/alanlawrence/factorial_hugr.json") as f:
        h = Hugr._from_serial(SerialHugr.load_json(json.loads(f.read())))
    outs = await PyRuntime().run_graph(h)
    assert outs == [IntVal(120, 5).to_value()]
