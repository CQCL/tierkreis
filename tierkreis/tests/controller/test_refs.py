from typing import NamedTuple
import pytest
from tierkreis.controller.data.core import TModel
from tierkreis.controller.data.graph import GraphData
from tierkreis.controller.data.refs import (
    BytesRef,
    FloatRef,
    ListRef,
    ModelRef,
    StrRef,
    equal,
    modelref_from_tmodel,
    IntRef,
)


class MixedTModel(NamedTuple):
    a: int = 5
    b: float = 5.6
    c: str = "dummy_str"
    d: bytes = b"dummy_bytes"

    m: IntRef = IntRef.from_value_ref(10, "value")
    n: FloatRef = FloatRef.from_value_ref(11, "value")
    o: StrRef = StrRef.from_value_ref(12, "value")
    p: BytesRef = BytesRef.from_value_ref(13, "value")


class MixedOutput(NamedTuple):
    a: IntRef = IntRef.from_value_ref(0, "value")
    b: FloatRef = FloatRef.from_value_ref(1, "value")
    c: StrRef = StrRef.from_value_ref(2, "value")
    d: BytesRef = BytesRef.from_value_ref(3, "value")

    m: IntRef = IntRef.from_value_ref(10, "value")
    n: FloatRef = FloatRef.from_value_ref(11, "value")
    o: StrRef = StrRef.from_value_ref(12, "value")
    p: BytesRef = BytesRef.from_value_ref(13, "value")


params: list[tuple[TModel, ModelRef]] = [
    (5, IntRef.from_value_ref(0, "value")),
    (IntRef.from_value_ref(0, "value"), IntRef.from_value_ref(0, "value")),
    (5.9, FloatRef.from_value_ref(0, "value")),
    (FloatRef.from_value_ref(0, "value"), FloatRef.from_value_ref(0, "value")),
    ("dummy_s", StrRef.from_value_ref(0, "value")),
    (StrRef.from_value_ref(0, "value"), StrRef.from_value_ref(0, "value")),
    (b"dummy_b", BytesRef.from_value_ref(0, "value")),
    (BytesRef.from_value_ref(0, "value"), BytesRef.from_value_ref(0, "value")),
    ([1, 2, 3], ListRef.from_value_ref(0, "value")),
    (ListRef.from_value_ref(0, "value"), ListRef.from_value_ref(0, "value")),
    (MixedTModel(), MixedOutput()),
]


@pytest.mark.parametrize("tmodel,ref", params)
def test_modelref_from_tmodel(tmodel: TModel, ref: ModelRef):
    g = GraphData()
    x = modelref_from_tmodel(g, tmodel)
    assert equal(x, ref)
