from typing import NamedTuple
import pytest
from tierkreis.controller.data.core import TModel, ValueRef
from tierkreis.controller.data.refs import modelref_from_tmodel


class MixedTModel(NamedTuple):
    a: int = 5
    b: float = 5.6
    c: str = "dummy_str"
    d: bytes = b"dummy_bytes"


# class MixedOutput(NamedTuple):
#     a: IntRef = (0, "value")
#     b: FloatRef = (1, "value")
#     c: StrRef = (2, "value")
#     d: BytesRef = (3, "value")

#     m: IntRef = (10, "value")
#     n: FloatRef = (11, "value")
#     o: StrRef = (12, "value")
#     p: BytesRef = (13, "value")


params: list[tuple[type[TModel], list[ValueRef]]] = [
    (int, [(0, "value")]),
    (float, [(0, "value")]),
    (str, [(0, "value")]),
    (bytes, [(0, "value")]),
    (bytearray, [(0, "value")]),
    (memoryview, [(0, "value")]),
    (bool, [(0, "value")]),
    (int, [(0, "value")]),
    (str, [(0, "value")]),
    (int, [(0, "value")]),
    (MixedTModel, [(0, "a"), (1, "b"), (2, "c"), (3, "d")]),
]


@pytest.mark.parametrize("tmodel,refs", params)
def test_modelref_from_tmodel(tmodel: type[TModel], refs: list[ValueRef]):
    x = modelref_from_tmodel(tmodel, refs)
    expected = refs if len(refs) > 1 else refs[0]
    assert tuple(x) == tuple(expected)
