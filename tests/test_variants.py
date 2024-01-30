from dataclasses import dataclass, field
from enum import Enum
from typing import Literal, Union

import pydantic as pyd
import pytest
from test_worker.main import (
    IntStruct,
)

from tierkreis.builder import Const, Output, UnionConst, graph
from tierkreis.client.runtime_client import RuntimeClient
from tierkreis.core.types import TierkreisType, UnionTag
from tierkreis.core.values import (
    FloatValue,
    IntValue,
    StringValue,
    StructValue,
    TierkreisValue,
    ToPythonFailure,
    VariantValue,
    VecValue,
    option_none,
)


@pytest.mark.asyncio
async def test_union_types(bi, client: RuntimeClient) -> None:
    # test structs containing unions can be converted to variant values, sent
    # through worker funcctions that process them as unions, and converted back
    # to unions.

    iv = TierkreisValue.from_python(1)
    assert iv.to_python(float | int) == 1
    fv = TierkreisValue.from_python(2.3)
    assert fv.to_python(int | float) == 2.3

    @dataclass
    class StructWithUnion:
        # redefine struct with Union[] syntax here to test both
        # (alongside A | B syntax)
        x: Union[IntStruct, float]

    pn = bi["python_nodes"]
    a_py = StructWithUnion(1.0)
    b_py = StructWithUnion(IntStruct(2))

    @graph()
    def g() -> Output:
        return Output(
            a=pn.id_union_struct(Const(a_py)), b=pn.id_union_struct(Const(b_py))
        )

    out = await client.run_graph(g)
    a, b = out["a"], out["b"]

    assert isinstance(a, StructValue)
    assert isinstance(b, StructValue)
    a_var = a.values["x"]
    assert isinstance(a_var, VariantValue)
    assert a_var.tag == UnionTag.prefix + "float"
    b_var = b.values["x"]
    assert isinstance(b_var, VariantValue)
    assert b_var.tag == UnionTag.prefix + "int_struct"

    assert a.to_python(StructWithUnion) == a_py
    assert b.to_python(StructWithUnion) == b_py

    for bad_tag in ("invalid_tag", UnionTag.type_tag(IntStruct)):
        with pytest.raises(ToPythonFailure):
            v: VariantValue = VariantValue(bad_tag, TierkreisValue.from_python(1.0))
            struct: StructValue = StructValue({"x": v})
            _ = struct.to_python(StructWithUnion)

    @dataclass
    class AmbiguousUnion:
        x: Union[list[int], list[bool]]

    with pytest.raises(ValueError, match="unique names"):
        TierkreisType.from_python(AmbiguousUnion)

    sig = await client.get_signature()

    @graph(type_check_sig=sig)
    def g2() -> Output:
        return Output(a=pn.id_union(UnionConst(1)), b=pn.id_union(UnionConst(1.0)))

    out = await client.run_graph(g2)
    a, b = out["a"], out["b"]
    assert a.to_python(int | float) == 1
    assert b.to_python(int | float) == 1.0


@pyd.dataclasses.dataclass(frozen=True, kw_only=True)
class ConstrainedField:
    foo: float
    bar: pyd.PositiveFloat | None = None
    points: tuple[float, ...]


@pyd.dataclasses.dataclass(frozen=True, kw_only=True)
class SimpleVariant(ConstrainedField):
    mean: float
    disc_name: Literal["Simple", "simple"] = field(default="Simple")


@pyd.dataclasses.dataclass(frozen=True, kw_only=True)
class ComplexVariant(ConstrainedField):
    mean: float
    variance: pyd.PositiveFloat
    foo: pyd.NonNegativeFloat
    disc_name: Literal["Complex"] = field(default="Complex", init=True)


class EnumExample(Enum):
    First = "First"
    Second = "Second"


class ContainsVariant(pyd.BaseModel):
    n: int
    enum: EnumExample
    variant: ComplexVariant | SimpleVariant = pyd.Field(discriminator="disc_name")


@pyd.dataclasses.dataclass(frozen=True, kw_only=True)
class NonInitPydField:
    xl: int = pyd.Field(default=0)
    non_init: int = field(default=0, init=False)


class Model(pyd.BaseModel):
    x: int
    y: NonInitPydField


class AnnotatedWithUnion(pyd.BaseModel):
    un: pyd.PositiveFloat | int


class AnnotatedInList(pyd.BaseModel):
    ul: list[pyd.PositiveFloat]


@pytest.mark.asyncio
async def test_pydantic_types(bi, client: RuntimeClient) -> None:
    constrained = ConstrainedField(foo=1, points=(1.2,))
    tk_constrained = StructValue(
        {
            "foo": FloatValue(1.0),
            "points": VecValue([FloatValue(1.2)]),
            "bar": option_none,
        }
    )

    cmplex = ComplexVariant(mean=-3.4, variance=4.5, **constrained.__dict__)
    tk_cmplex = StructValue(
        {
            "mean": FloatValue(-3.4),
            "variance": FloatValue(4.5),
            "disc_name": StringValue("Complex"),
            **tk_constrained.values,
        }
    )

    simple = SimpleVariant(mean=1.3, **constrained.__dict__)
    tk_simple = StructValue(
        {
            **tk_constrained.values,
            "mean": FloatValue(1.3),
            "disc_name": StringValue("Simple"),
        }
    )

    contains = ContainsVariant(variant=cmplex, n=4, enum=EnumExample.First)

    tk_first = VariantValue("First", StructValue({}))
    tk_contains = StructValue(
        {
            "variant": VariantValue("Complex", tk_cmplex),
            "n": IntValue(4),
            "enum": tk_first,
        }
    )

    contains_alt = ContainsVariant(variant=simple, n=4, enum=EnumExample.Second)
    tk_second = VariantValue("Second", StructValue({}))
    tk_contains_alt = StructValue(
        {
            "variant": VariantValue("Simple", tk_simple),
            "n": IntValue(4),
            "enum": tk_second,
        }
    )

    da = NonInitPydField()
    tk_da = StructValue(
        {
            "xl": IntValue(0),
            "non_init": IntValue(0),
        }
    )

    tk_model = StructValue(
        {
            "x": IntValue(1),
            "y": tk_da,
        }
    )

    tk_list_model = StructValue(
        {
            "ul": VecValue([FloatValue(1.2)]),
        }
    )

    tk_union_model = StructValue(
        {
            "un": VariantValue(UnionTag.type_tag(int), IntValue(1)),
        }
    )
    samples = [
        (ConstrainedField, constrained, tk_constrained),
        (SimpleVariant, simple, tk_simple),
        (
            EnumExample,
            EnumExample.First,
            tk_first,
        ),
        (EnumExample, EnumExample.Second, tk_second),
        (ComplexVariant, cmplex, tk_cmplex),
        (ContainsVariant, contains, tk_contains),
        (ContainsVariant, contains_alt, tk_contains_alt),
        (NonInitPydField, da, tk_da),
        (Model, Model(x=1, y=da), tk_model),
        (AnnotatedInList, AnnotatedInList(ul=[1.2]), tk_list_model),
        (AnnotatedWithUnion, AnnotatedWithUnion(un=1), tk_union_model),
    ]
    for py_type, py_val, tk_val in samples:
        _ = TierkreisType.from_python(py_type)
        tv = TierkreisValue.from_python(py_val)
        assert tv == tk_val
        assert tv.to_python(py_type) == py_val

        pn = bi["python_nodes"]

        @graph()
        def g() -> Output:
            return Output(pn.id_py(Const(py_val)))

        out = (await client.run_graph(g))["value"]

        assert out.to_python(py_type) == py_val
