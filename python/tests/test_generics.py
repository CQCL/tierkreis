from dataclasses import dataclass
from typing import Generic, Type, TypeVar, cast

import pydantic as pyd
import pytest
from test_worker.main import (
    MyGeneric,
    MyGenericList,
)

from tierkreis.builder import Const, Output, graph
from tierkreis.client.runtime_client import RuntimeClient
from tierkreis.core._internal import generic_origin
from tierkreis.core.types import (
    IntType,
    Row,
    StructType,
    TierkreisType,
    VarType,
    VecType,
)
from tierkreis.core.values import (
    IncompatibleAnnotatedValue,
    IntValue,
    StructValue,
    TierkreisValue,
    VecValue,
)


@pytest.mark.asyncio
async def test_generic(bi, client: RuntimeClient) -> None:
    py_type = MyGeneric[int]
    py_val = MyGeneric(x=1)
    py_val_explicit_type = MyGeneric[int](x=1)
    tk_val = StructValue(
        {
            "x": IntValue(1),
        }
    )
    tk_ty = StructType(shape=Row({"x": IntType()}), name="MyGeneric[int]")

    assert TierkreisType.from_python(py_type) == tk_ty
    assert TierkreisValue.from_python(py_val, py_type) == tk_val
    with pytest.raises(IncompatibleAnnotatedValue, match="~G"):
        # value doesn't know it is instance of concrete type so fails.
        TierkreisValue.from_python(py_val)
    # whereas the pydantic-validated instantiation records its own concrete type
    assert TierkreisValue.from_python(py_val_explicit_type) == tk_val
    assert tk_val.to_python(py_type) == py_val

    on = bi["python_nodes"]

    @graph()
    def g() -> Output:
        return Output(on.generic_int_to_str(Const(py_val, py_type)))

    out = (await client.run_graph(g))["value"]

    assert out.to_python(MyGeneric[str]) == MyGeneric(x="got number: 1")


@pytest.mark.asyncio
async def test_generic_list(bi, client: RuntimeClient) -> None:
    py_type = MyGenericList[int]
    py_val = MyGenericList(x=[1])
    py_val_explicit_type = MyGenericList[int](x=[1])
    tk_val = StructValue(
        {
            "x": VecValue([IntValue(1)]),
        }
    )
    tk_ty = StructType(shape=Row({"x": VecType(IntType())}), name="MyGenericList[int]")

    assert TierkreisType.from_python(py_type) == tk_ty
    assert TierkreisValue.from_python(py_val, py_type) == tk_val
    with pytest.raises(IncompatibleAnnotatedValue, match="~G"):
        # value doesn't know it is instance of concrete type so fails.
        TierkreisValue.from_python(py_val)
    # whereas the pydantic-validated instantiation records its own concrete type
    assert TierkreisValue.from_python(py_val_explicit_type) == tk_val
    assert tk_val.to_python(py_type) == py_val

    on = bi["python_nodes"]

    @graph()
    def g() -> Output:
        return Output(on.generic_int_to_str_list(Const(py_val, py_type)))

    out = (await client.run_graph(g))["value"]

    assert out.to_python(MyGenericList[str]) == MyGenericList(x=["got number: 1"])


@pytest.mark.xfail(reason="generic dataclasses aren't supported - only pydantic models")
def test_generic_dataclass() -> None:
    from typing import Generic, TypeVar

    T = TypeVar("T")

    @dataclass
    class MyGenericDataclass(Generic[T]):
        x: T

    assert TierkreisType.from_python(MyGenericDataclass[int]) == StructType(
        shape=Row({"x": VarType("T")}), name="MyGenericDataclass"
    )
    tk_val = StructValue(
        {
            "x": IntValue(1),
        }
    )
    py_val = MyGenericDataclass(x=1)
    # both asserts below fail
    assert tk_val.to_python(MyGenericDataclass[int]) == py_val
    assert TierkreisValue.from_python(py_val, MyGenericDataclass[int]) == tk_val


def test_pydantic_nested() -> None:
    T = TypeVar("T")

    class Inner(pyd.BaseModel, Generic[T]):
        items: list[T]  # Something type-erased

    class Outer(pyd.BaseModel, Generic[T]):
        val: Inner[T]

    # All these pass type checking (consistent with type erasure):
    # (Note: make_inner_ab: a,b = presence of annotation on constructor, return-type)
    def make_inner_validated() -> Inner:
        return Inner[int](items=[3, 4, 5])

    def make_inner() -> Inner[int]:
        return Inner(items=[3, 5, 7])

    # Pydantic is happy with all these at runtime:
    un_un: Outer = Outer(val=make_inner())
    val_un: Outer = Outer(val=make_inner_validated())
    val_val: Outer = Outer[int](val=make_inner_validated())

    # pydantic is happy with all of these at runtime;
    # Tierkreis can convert only the validated without an explicit type annotation
    for o in [un_un, val_un]:
        with pytest.raises(IncompatibleAnnotatedValue):
            TierkreisValue.from_python(o)
    tk_val = TierkreisValue.from_python(val_val)
    assert tk_val.to_python(Outer[int]) == val_val  # and back (with explicit type)

    # Tierkreis can convert any of them with an explicit type annotation:
    for o in [un_un, val_un, val_val]:
        tk_val = TierkreisValue.from_python(o, Outer[int])
        assert tk_val.to_python(Outer[int]) == o

    # And pydantic rejects this one at runtime:
    with pytest.raises(
        pyd.ValidationError,
        match=r"Input should be a valid dictionary or instance of Inner\[int\]",
    ):
        Outer[int](val=make_inner())


def test_generic_origin() -> None:
    assert generic_origin(list[int]) is list
    assert generic_origin(list) is None

    @dataclass
    class MyDataclass:
        foo: int

    assert generic_origin(MyDataclass) is None

    T = TypeVar("T")

    @dataclass
    class MyGenericDataclass(Generic[T]):
        item: T

    assert generic_origin(MyGenericDataclass[int]) == MyGenericDataclass
    assert generic_origin(MyGenericDataclass) is None

    class MyModel(pyd.BaseModel):
        f: int

    assert generic_origin(MyModel) is None

    class MyGenericModel(pyd.BaseModel, Generic[T]):
        items: list[T]

    assert generic_origin(MyGenericModel[int]) == MyGenericModel
    assert generic_origin(MyGenericModel) is None

    assert generic_origin(cast(Type, T)) is None
