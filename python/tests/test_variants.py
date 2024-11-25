import re
import warnings
from dataclasses import dataclass, field
from enum import Enum
from types import UnionType
from typing import Any, Literal, Type, Union

import pydantic as pyd
import pytest
from test_worker.main import EmptyStruct, IntStruct, MyGeneric

from tierkreis.builder import Const, Output, UnionConst, graph
from tierkreis.client.runtime_client import RuntimeClient
from tierkreis.core.opaque_model import OpaqueModel
from tierkreis.core.types import IncompatibleUnionType, TierkreisType, UnionTag
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
    # through worker functions that process them as unions, and converted back
    # to unions.
    iv = TierkreisValue.from_python(1)
    assert iv.to_python_union(float | int) == 1
    fv = TierkreisValue.from_python(2.3)
    assert fv.to_python_union(int | float) == 2.3

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

    with pytest.raises(IncompatibleUnionType):
        TierkreisType.from_python(AmbiguousUnion)

    sig = await client.get_signature()

    @graph(type_check_sig=sig)
    def g2() -> Output:
        return Output(a=pn.id_union(UnionConst(1)), b=pn.id_union(UnionConst(1.0)))

    out = await client.run_graph(g2)
    a, b = out["a"], out["b"]
    assert a.to_python_union(int | float) == 1
    assert b.to_python_union(int | float) == 1.0


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


class OpaqueContainsVariant(OpaqueModel):
    n: int
    enum: EnumExample
    variant: ComplexVariant | SimpleVariant = pyd.Field(discriminator="disc_name")


def _tktype_from_py(py_type: UnionType | Type) -> TierkreisType:
    if isinstance(py_type, UnionType):
        return TierkreisType.from_python_union(py_type)
    return TierkreisType.from_python(py_type)


def _tkval_from_py(py_val: Any, py_type: UnionType | Type | None) -> TierkreisValue:
    if isinstance(py_type, UnionType):
        return TierkreisValue.from_python_union(py_val, py_type)
    return TierkreisValue.from_python(py_val, py_type)


def _tkval_to_py(tkv: TierkreisValue, py_type: UnionType | Type) -> Any:
    if isinstance(py_type, UnionType):
        return tkv.to_python_union(py_type)
    return tkv.to_python(py_type)


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
    opaque_contains = OpaqueContainsVariant(variant=cmplex, n=4, enum=EnumExample.First)

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
    tk_opaque_contains = StructValue(
        {
            "__tk_opaque_opaque_contains_variant": StringValue(
                opaque_contains.model_dump_json()
            ),
        }
    )

    def mk_mygeneric_variant(typ: Type, val: TierkreisValue) -> StructValue:
        return StructValue({"x": VariantValue(UnionTag.type_tag(typ), val)})

    samples: list[tuple[Type | UnionType, Any, TierkreisValue]] = [
        (ConstrainedField, constrained, tk_constrained),
        (SimpleVariant, simple, tk_simple),
        (EnumExample, EnumExample.First, tk_first),
        (EnumExample, EnumExample.Second, tk_second),
        (ComplexVariant, cmplex, tk_cmplex),
        (ContainsVariant, contains, tk_contains),
        (ContainsVariant, contains_alt, tk_contains_alt),
        (NonInitPydField, da, tk_da),
        (Model, Model(x=1, y=da), tk_model),
        (AnnotatedInList, AnnotatedInList(ul=[1.2]), tk_list_model),
        (AnnotatedWithUnion, AnnotatedWithUnion(un=1), tk_union_model),
        (
            OpaqueContainsVariant,
            opaque_contains,
            tk_opaque_contains,
        ),
        (EnumExample | None, EnumExample.First, tk_first),
        # (None | EnumExample, EnumExample.First, tk_first), # fails, see test_reversed_union
        (EnumExample | None, None, option_none),
        (None | EnumExample, None, option_none),
    ]

    for py_type, py_val, expected_tk_val in samples:
        _ = _tktype_from_py(py_type)
        converted_tk_val = TierkreisValue.from_python(py_val)
        assert converted_tk_val == expected_tk_val
        assert _tkval_from_py(py_val, py_type) == expected_tk_val
        assert _tkval_to_py(converted_tk_val, py_type) == py_val

        pn = bi["python_nodes"]

        @graph()
        def g() -> Output:
            return Output(pn.id_py(Const(py_val)))

        out = (await client.run_graph(g))["value"]

        assert _tkval_to_py(out, py_type) == py_val


def test_union_over_arguments() -> None:
    values = [MyGeneric[int](x=3), MyGeneric[str](x="foo")]
    types = [
        t
        for base in [MyGeneric[int] | MyGeneric[str], MyGeneric[str] | MyGeneric[int]]
        for t in [base, base | None, None | base]
    ]

    for val in values:
        for typ in types:
            tk_val = TierkreisValue.from_python_union(val, typ)
            assert tk_val.to_python_union(typ) == val

            # Separately test value+typ embedded together in an outer MyGeneric
            typ2 = MyGeneric[typ]  # type: ignore
            val2 = typ2(x=val)
            tk_val2 = TierkreisValue.from_python(val2, typ2)
            assert tk_val2.to_python(typ2) == val2


@pytest.mark.xfail(reason="See issue #454")
def test_reversed_union_enum() -> None:
    # This should be an entry in test:pydantic_types, if it worked:
    # (None | EnumExample, EnumExample.First, tk_first)
    tk_first = VariantValue("First", StructValue({}))
    py_type, py_val, expected_tk_val = (None | EnumExample, EnumExample.First, tk_first)
    assert TierkreisValue.from_python(py_val) == expected_tk_val
    # Works the right way around:
    assert expected_tk_val.to_python_union(EnumExample | None) == py_val
    # But reverse the union and it does not (result is "None")
    assert expected_tk_val.to_python_union(py_type) == py_val


def test_pydantic_generic_union() -> None:
    # Similar to above but from_python with explicit 'typ'
    # avoids the need for pydantic validation
    val = MyGeneric(x=MyGeneric[float](x=3.2))
    typ = MyGeneric[MyGeneric[int] | MyGeneric[float]]
    tk_val = TierkreisValue.from_python(val, typ)
    assert tk_val.to_python(typ) == val


@pytest.mark.asyncio
async def test_return_union(bi, client: RuntimeClient) -> None:
    # test a worker function declared as returning a union type,
    # correctly converts the return value

    sig = await client.get_signature()
    pn = bi["python_nodes"]

    @graph(type_check_sig=sig)
    def g() -> Output:
        return Output(b=pn.zero_to_empty(x=Const(0)), a=pn.zero_to_empty(x=Const(1)))

    out = await client.run_graph(g)

    a, b = out["a"], out["b"]

    assert isinstance(a, VariantValue)
    assert a.tag == UnionTag.type_tag(IntStruct)
    assert isinstance(b, VariantValue)
    assert b.tag == UnionTag.type_tag(EmptyStruct)

    # to_python is tag-driven so ordering of union elements makes no difference
    assert a.to_python_union(IntStruct | EmptyStruct) == IntStruct(1)
    assert a.to_python_union(EmptyStruct | IntStruct) == IntStruct(1)
    assert b.to_python_union(IntStruct | EmptyStruct) == EmptyStruct()


# Make sure that the ordering of Union elements doesn't affect anything here
@pytest.mark.parametrize(
    "union_type", [IntStruct | EmptyStruct, EmptyStruct | IntStruct]
)
def test_warnings(union_type: Type) -> None:
    with warnings.catch_warnings(record=True) as ws:
        val = TierkreisValue.from_python(IntStruct(3), union_type)
    assert len(ws) == 0
    assert val == VariantValue(
        UnionTag.type_tag(IntStruct), StructValue({"y": IntValue(3)})
    )

    @dataclass
    class IntSubStruct(IntStruct):
        new_field: float

    with warnings.catch_warnings(record=True) as ws:
        val = TierkreisValue.from_python(IntSubStruct(13, 4.21), union_type)
    assert len(ws) == 1
    assert re.search("IntSubStruct.*beyond those in.*IntStruct", str(ws[0]))
    assert val == VariantValue(
        UnionTag.type_tag(IntStruct), StructValue({"y": IntValue(13)})
    )


@pytest.mark.asyncio
async def test_union_generic_basemodel(sig, bi, client: RuntimeClient) -> None:
    msg = "Hello World!"

    @graph(type_check_sig=sig)
    def main() -> Output:
        res = bi["python_nodes"].echo_union(Const(msg))
        return Output(res)

    res = await client.run_graph(main)
    assert res.pop("value").to_python_union(MyGeneric[str] | int) == MyGeneric[str](
        x=msg
    )
    assert res == {}  # No other outputs besides x
