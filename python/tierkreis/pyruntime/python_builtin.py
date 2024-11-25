"""Implementation of builtin namespace in python."""

import asyncio
from copy import deepcopy
from dataclasses import dataclass
from typing import Generic, TypeVar, cast

from tierkreis.core.protos.tierkreis.v1alpha1.graph import (
    Constraint,
    Empty,
    GraphType,
    Kind,
    PartitionConstraint,
    RowType,
    StructType,
    Type,
    TypeScheme,
    TypeSchemeVar,
)
from tierkreis.core.protos.tierkreis.v1alpha1.signature import FunctionDeclaration
from tierkreis.core.python import RuntimeGraph
from tierkreis.core.tierkreis_graph import GraphValue, IncomingWireType, TierkreisGraph
from tierkreis.core.types import StarKind, TierkreisPair, UnpackRow
from tierkreis.core.utils import map_vals
from tierkreis.core.values import StructValue
from tierkreis.worker.namespace import Function, Namespace

namespace = Namespace()

a = TypeVar("a")
b = TypeVar("b")
val = TypeVar("val")
key = TypeVar("key")


@namespace.function(name="and")
async def _and(a: bool, b: bool) -> bool:
    """Check a and b are true; a && b"""
    return a and b


@dataclass
class CopyOut(Generic[a], UnpackRow):
    value_0: a
    value_1: a


@namespace.function(type_vars={"a": StarKind()})
async def copy(value: a) -> CopyOut[a]:
    "Copies its input value to each of its two outputs."
    return CopyOut(value, deepcopy(value))


@dataclass
class EmptyOut(Generic[a], UnpackRow):
    pass


@namespace.function(type_vars={"a": StarKind()})
async def discard(value: a) -> EmptyOut[a]:
    """Ignores its input value, has no outputs."""
    # things won't actually be deleted until python decides to
    return EmptyOut()


@dataclass
class EqOut(UnpackRow):
    result: bool


@namespace.function(type_vars={"val": StarKind()})
async def eq(value_0: val, value_1: val) -> EqOut:
    """Check two input values of the same type for equality, \
producing a boolean."""
    return EqOut(value_0 == value_1)


async def _eval(_client, _stack, _x: StructValue) -> StructValue:
    # implemented as part of runtime
    raise NotImplementedError


namespace.functions["eval"] = Function(
    run=_eval,
    declaration=FunctionDeclaration(
        type_scheme=TypeScheme(
            variables=[
                TypeSchemeVar(name="in", kind=Kind(row=Empty())),
                TypeSchemeVar(name="out", kind=Kind(row=Empty())),
            ],
            body=Type(
                graph=GraphType(
                    inputs=RowType(
                        content={
                            "thunk": Type(
                                graph=GraphType(
                                    inputs=RowType(rest="in"),
                                    outputs=RowType(rest="out"),
                                )
                            )
                        },
                        rest="in",
                    ),
                    outputs=RowType(rest="out"),
                )
            ),
        ),
        description="Evaluates the graph on the `thunk` input with other inputs "
        "matching the graph inputs, producing outputs matching those of the graph.",
        input_order=["thunk"],
    ),
)


@namespace.function()
async def fadd(a: float, b: float) -> float:
    """Add floats a and b together; a + b"""
    return a + b


@namespace.function()
async def fdiv(a: float, b: float) -> float:
    """float division of a by b; a / b"""
    return a / b


@namespace.function()
async def fgeq(a: float, b: float) -> bool:
    """Check if a is greater than or equal to b; a >= b"""
    return a >= b


@namespace.function()
async def fgt(a: float, b: float) -> bool:
    """Check if a is greater than b; a > b"""
    return a > b


@namespace.function()
async def fleq(a: float, b: float) -> bool:
    """Check if a is less than or equal to b; a <= b"""
    return a <= b


@namespace.function()
async def float_to_int(float: float) -> int:
    """Convert a float to an integer"""
    return int(float)


@namespace.function()
async def flt(a: float, b: float) -> bool:
    """Check if a is less than b; a < b"""
    return a < b


@namespace.function()
async def fmod(a: float, b: float) -> float:
    """Modulo of a by b; a % b"""
    return a % b


@namespace.function()
async def fmul(a: float, b: float) -> float:
    """Multiply floats a and b together; a * b"""
    return a * b


@namespace.function()
async def fpow(a: float, b: float) -> float:
    """Exponentiate a by power b; a ^ b"""
    return a**b


@namespace.function()
async def fsub(a: float, b: float) -> float:
    """Subtract float b from float a; a - b"""
    return a - b


@namespace.function()
async def iadd(a: int, b: int) -> int:
    """Add integers a and b together; a + b"""
    return a + b


@namespace.function("id", type_vars={"a": StarKind()})
async def _id(value: a) -> a:
    """Passes a single, arbitrary, value from input to output."""
    return value


@namespace.function(type_vars={"a": StarKind()})
async def sleep(value: a, delay_secs: float) -> a:
    """Identity function with an asynchronous delay input in seconds."""
    await asyncio.sleep(delay_secs)
    return value


@namespace.function()
async def idiv(a: int, b: int) -> int:
    """Integer division of a by b; a / b"""
    return a // b


@namespace.function()
async def igeq(a: int, b: int) -> bool:
    """Check if a is greater than or equal to b; a >= b"""
    return a >= b


@namespace.function()
async def igt(a: int, b: int) -> bool:
    """Check if a is greater than b; a > b"""
    return a > b


@namespace.function()
async def ileq(a: int, b: int) -> bool:
    """Check if a is less than or equal to b; a <= b"""
    return a <= b


@namespace.function()
async def ilt(a: int, b: int) -> bool:
    """Check if a is less than b; a < b"""
    return a < b


@namespace.function()
async def imod(a: int, b: int) -> int:
    """Modulo of a by b; a % b"""
    return a % b


@namespace.function()
async def imul(a: int, b: int) -> int:
    """Multiply integers a and b together; a * b"""
    return a * b


@dataclass()
class _InsertOut(Generic[a, b], UnpackRow):
    map: dict[a, b]


@namespace.function(type_vars={"a": StarKind(), "b": StarKind()})
async def insert_key(map: dict[a, b], key: a, val: b) -> _InsertOut[a, b]:
    """Transforms an input `Map` into an output by adding an \
entry (or replacing an existing one) for an input key and value."""
    map[key] = val
    return _InsertOut(map)


@namespace.function()
async def int_to_float(int: int) -> float:
    """Convert an integer to a float"""
    return float(int)


@namespace.function()
async def ipow(a: int, b: int) -> int:
    """Exponentiate a by power b; a ^ b. b must be a positive integer."""
    return a**b


@namespace.function()
async def isub(a: int, b: int) -> int:
    """Subtract integer b from integer a; a - b"""
    return a - b


async def _loop(_client, _stack, _x: StructValue) -> StructValue:
    # implemented as part of runtime
    raise NotImplementedError


namespace.functions["loop"] = Function(
    run=_loop,
    declaration=FunctionDeclaration(
        type_scheme=TypeScheme(
            variables=[
                TypeSchemeVar(name="loop_var", kind=Kind(star=Empty())),
                TypeSchemeVar(name="result", kind=Kind(star=Empty())),
            ],
            body=Type(
                graph=GraphType(
                    inputs=RowType(
                        content={
                            "body": Type(
                                graph=GraphType(
                                    inputs=RowType(
                                        content={"value": Type(var="loop_var")}
                                    ),
                                    outputs=RowType(
                                        content={
                                            "value": Type(
                                                variant=RowType(
                                                    content={
                                                        "break": Type(var="result"),
                                                        "continue": Type(
                                                            var="loop_var"
                                                        ),
                                                    }
                                                )
                                            )
                                        }
                                    ),
                                )
                            ),
                            "value": Type(var="loop_var"),
                        }
                    ),
                    outputs=RowType(content={"value": Type(var="result")}),
                )
            ),
        ),
        description="Repeatedly applies a `Graph` input while it produces \
a `Variant` tagged `continue`, i.e. until it returns a value tagged `break`, \
and then returns that value.",
        input_order=["body", "value"],
        output_order=["value"],
    ),
)


@dataclass
class _MakePairOut(Generic[a, b], UnpackRow):
    pair: TierkreisPair[a, b]


@namespace.function(type_vars={"a": StarKind(), "b": StarKind()})
async def make_pair(first: a, second: b) -> _MakePairOut[a, b]:
    """Makes an output `Pair` from two separate inputs."""
    return _MakePairOut(TierkreisPair(first, second))


async def make_struct(_client, _stack, ins: StructValue) -> StructValue:
    """Construct a struct from incoming ports."""
    return StructValue({"struct": ins})


namespace.functions["make_struct"] = Function(
    run=make_struct,
    declaration=FunctionDeclaration(
        type_scheme=TypeScheme(
            variables=[TypeSchemeVar(name="fields", kind=Kind(row=Empty()))],
            body=Type(
                graph=GraphType(
                    inputs=RowType(rest="fields"),
                    outputs=RowType(
                        content={
                            "struct": Type(
                                struct=StructType(shape=RowType(rest="fields"))
                            )
                        }
                    ),
                )
            ),
        ),
        description="Takes any number of inputs and produces a single `Struct` "
        "output with a field for each input, field names matching input ports.",
        output_order=["struct"],
    ),
)


@namespace.function(type_vars={"val": StarKind()})
async def neq(value_0: val, value_1: val) -> EqOut:
    """Check two values are not equal."""
    return EqOut(value_0 != value_1)


@namespace.function("or")
async def _or(a: bool, b: bool) -> bool:
    """Check a or b are true; a || b"""
    return a or b


async def _partial(_client, _stack, inputs: StructValue) -> StructValue:
    invals = inputs.values
    thunk = deepcopy(cast(GraphValue, invals.pop("thunk")).value)
    newg = TierkreisGraph()
    rest_inputs = [port for port in thunk.inputs() if port not in invals]
    inports = map_vals(invals, lambda x: newg.add_const(x)["value"])
    inports.update({port: newg.input[port] for port in rest_inputs})
    outs = newg.insert_graph(thunk, **inports)
    newg.set_outputs(**outs)
    return StructValue({"value": GraphValue(newg)})


namespace.functions["partial"] = Function(
    run=_partial,
    declaration=FunctionDeclaration(
        type_scheme=TypeScheme(
            variables=[
                TypeSchemeVar(name="in_given", kind=Kind(row=Empty())),
                TypeSchemeVar(name="in_rest", kind=Kind(row=Empty())),
                TypeSchemeVar(name="in", kind=Kind(row=Empty())),
                TypeSchemeVar(name="outv", kind=Kind(row=Empty())),
            ],
            constraints=[
                Constraint(
                    partition=PartitionConstraint(
                        left=Type(var="in_given"),
                        right=Type(var="in_rest"),
                        union=Type(var="in"),
                    )
                )
            ],
            body=Type(
                graph=GraphType(
                    inputs=RowType(
                        content={
                            "thunk": Type(
                                graph=GraphType(
                                    inputs=RowType(rest="in"),
                                    outputs=RowType(rest="outv"),
                                )
                            )
                        },
                        rest="in_given",
                    ),
                    outputs=RowType(
                        content={
                            "value": Type(
                                graph=GraphType(
                                    inputs=RowType(rest="in_rest"),
                                    outputs=RowType(rest="outv"),
                                )
                            )
                        }
                    ),
                )
            ),
        ),
        description="Partial application;"
        " output a new graph with some input values injected as constants",
        input_order=["thunk"],
        output_order=["value"],
    ),
)


@dataclass
class _PopOut(Generic[a], UnpackRow):
    vec: list[a]
    item: a


@namespace.function(type_vars={"a": StarKind()})
async def pop(vec: list[a]) -> _PopOut[a]:
    """Pops the first element from an input `Vec`, returning said \
element separately from the remainder `Vec`. Fails at runtime if the input `Vec` \
is empty."""
    item = vec.pop()
    return _PopOut(vec, item)


@dataclass
class _PushOut(Generic[a], UnpackRow):
    vec: list[a]


@namespace.function(type_vars={"a": StarKind()})
async def push(vec: list[a], item: a) -> _PushOut[a]:
    """Adds an input element onto an input `Vec` to give an output `Vec`."""
    vec.append(item)
    return _PushOut(vec)


@dataclass
class _RemoveOut(Generic[a, b], UnpackRow):
    map: dict[a, b]
    val: b


@namespace.function(type_vars={"a": StarKind(), "b": StarKind()})
async def remove_key(map: dict[a, b], key: a) -> _RemoveOut[a, b]:
    """Remove a key (input) from a map (input), return the map and value."""
    val = map.pop(key)
    return _RemoveOut(map, val)


async def _sequence(_client, _stack, inputs: StructValue) -> StructValue:
    invals = cast(dict[str, IncomingWireType], inputs.values)
    first = deepcopy(cast(GraphValue, invals.pop("first")).value)
    second = deepcopy(cast(GraphValue, invals.pop("second")).value)
    newg = TierkreisGraph()
    outs1 = newg.insert_graph(
        first, **{port: newg.input[port] for port in first.inputs()}
    )
    outs2 = newg.insert_graph(second, **outs1)
    newg.set_outputs(**outs2)
    return StructValue({"sequenced": GraphValue(newg)})


namespace.functions["sequence"] = Function(
    run=_sequence,
    declaration=FunctionDeclaration(
        type_scheme=TypeScheme(
            variables=[
                TypeSchemeVar(name="in", kind=Kind(row=Empty())),
                TypeSchemeVar(name="middle", kind=Kind(row=Empty())),
                TypeSchemeVar(name="out", kind=Kind(row=Empty())),
            ],
            body=Type(
                graph=GraphType(
                    inputs=RowType(
                        content={
                            "second": Type(
                                graph=GraphType(
                                    inputs=RowType(rest="middle"),
                                    outputs=RowType(rest="out"),
                                )
                            ),
                            "first": Type(
                                graph=GraphType(
                                    inputs=RowType(rest="in"),
                                    outputs=RowType(rest="middle"),
                                )
                            ),
                        }
                    ),
                    outputs=RowType(
                        content={
                            "sequenced": Type(
                                graph=GraphType(
                                    inputs=RowType(rest="in"),
                                    outputs=RowType(rest="out"),
                                )
                            )
                        }
                    ),
                )
            ),
        ),
        description="Sequence two graphs, where the"
        " outputs of the first graph match the inputs of the second.",
        input_order=["first", "second"],
        output_order=["sequenced"],
    ),
)


async def _parallel(_client, _stack, inputs: StructValue) -> StructValue:
    invals = inputs.values
    left = deepcopy(cast(GraphValue, invals.pop("left")).value)
    right = deepcopy(cast(GraphValue, invals.pop("right")).value)
    newg = TierkreisGraph()
    outs1 = newg.insert_graph(
        left, **{port: newg.input[port] for port in left.inputs()}
    )
    outs2 = newg.insert_graph(
        right, **{port: newg.input[port] for port in right.inputs()}
    )
    newg.set_outputs(**outs1, **outs2)
    return StructValue({"value": GraphValue(newg)})


namespace.functions["parallel"] = Function(
    run=_parallel,
    declaration=FunctionDeclaration(
        type_scheme=TypeScheme(
            variables=[
                TypeSchemeVar(name="left_in", kind=Kind(row=Empty())),
                TypeSchemeVar(name="left_out", kind=Kind(row=Empty())),
                TypeSchemeVar(name="right_in", kind=Kind(row=Empty())),
                TypeSchemeVar(name="right_out", kind=Kind(row=Empty())),
                TypeSchemeVar(name="value_in", kind=Kind(row=Empty())),
                TypeSchemeVar(name="value_out", kind=Kind(row=Empty())),
            ],
            constraints=[
                Constraint(
                    partition=PartitionConstraint(
                        left=Type(var="left_in"),
                        right=Type(var="right_in"),
                        union=Type(var="value_in"),
                    )
                ),
                Constraint(
                    partition=PartitionConstraint(
                        left=Type(var="left_out"),
                        right=Type(var="right_out"),
                        union=Type(var="value_out"),
                    )
                ),
            ],
            body=Type(
                graph=GraphType(
                    inputs=RowType(
                        content={
                            "left": Type(
                                graph=GraphType(
                                    inputs=RowType(rest="left_in"),
                                    outputs=RowType(rest="left_out"),
                                )
                            ),
                            "right": Type(
                                graph=GraphType(
                                    inputs=RowType(rest="right_in"),
                                    outputs=RowType(rest="right_out"),
                                )
                            ),
                        }
                    ),
                    outputs=RowType(
                        content={
                            "value": Type(
                                graph=GraphType(
                                    inputs=RowType(rest="value_in"),
                                    outputs=RowType(rest="value_out"),
                                )
                            )
                        }
                    ),
                )
            ),
        ),
        description="Merges two input `Graph`s into a single output `Graph` "
        "with the disjoint union of their inputs and similarly their outputs.",
        input_order=["left", "right"],
        output_order=["value"],
    ),
)


@namespace.function(type_vars={"a": StarKind()})
async def switch(pred: bool, if_true: a, if_false: a) -> a:
    """Passes one or other of two inputs through according to a \
third, boolean, input."""
    return if_true if pred else if_false


@dataclass
class _UnpackPairOut(Generic[a, b], UnpackRow):
    first: a
    second: b


@namespace.function(type_vars={"a": StarKind(), "b": StarKind()})
async def unpack_pair(pair: TierkreisPair[a, b]) -> _UnpackPairOut[a, b]:
    "Splits an input `Pair` into two separate outputs."
    return _UnpackPairOut(pair.first, pair.second)


async def _unpack_struct(_client, _stack, ins: StructValue) -> StructValue:
    return cast(StructValue, ins.values["struct"])


namespace.functions["unpack_struct"] = Function(
    run=_unpack_struct,
    declaration=FunctionDeclaration(
        type_scheme=TypeScheme(
            variables=[TypeSchemeVar(name="fields", kind=Kind(row=Empty()))],
            body=Type(
                graph=GraphType(
                    inputs=RowType(
                        content={
                            "struct": Type(
                                struct=StructType(shape=RowType(rest="fields"))
                            )
                        }
                    ),
                    outputs=RowType(rest="fields"),
                )
            ),
        ),
        description="Destructure a single `Struct` input, outputting one value "
        "per field in the input, output ports matching field names.",
        input_order=["struct"],
    ),
)


@namespace.function()
async def xor(a: bool, b: bool) -> bool:
    """Check either a or b are true; a ^ b"""
    return a ^ b


@dataclass
class GraphIn(Generic[a], UnpackRow):
    value: a


@dataclass
class GraphOut(Generic[b], UnpackRow):
    value: b


@namespace.function(name="map", type_vars={"a": StarKind(), "b": StarKind()})
async def _map(thunk: RuntimeGraph[GraphIn[a], GraphOut[b]], value: list[a]) -> list[b]:
    """Runs a Graph input on each element of a `Vec` input and \
collects the results into a `Vec` output."""
    # We avoid the use of callbacks in the python builtins and so must
    # define map in the pyruntime
    raise NotImplementedError()
