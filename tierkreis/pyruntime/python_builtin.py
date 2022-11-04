"""Implementation of builtin namespace in python."""

from copy import deepcopy
from dataclasses import dataclass
from typing import Generic, TypeVar, cast

from tierkreis.core.protos.tierkreis.v1alpha.graph import (
    Constraint,
    Empty,
    GraphType,
    Kind,
    PairType,
    PartitionConstraint,
    RowType,
    StructType,
    Type,
    TypeScheme,
    TypeSchemeVar,
)
from tierkreis.core.protos.tierkreis.v1alpha.signature import FunctionDeclaration
from tierkreis.core.tierkreis_graph import GraphValue, IncomingWireType, TierkreisGraph
from tierkreis.core.tierkreis_struct import TierkreisStruct
from tierkreis.core.types import StarKind
from tierkreis.core.utils import map_vals
from tierkreis.core.values import MapValue, StructValue
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
class CopyOut(TierkreisStruct, Generic[a]):
    value_0: a
    value_1: a


@namespace.function(type_vars={"a": StarKind()})
async def copy(value: a) -> CopyOut[a]:
    "Copies its input value."
    return CopyOut(value, deepcopy(value))


@dataclass
class EmptyOut(TierkreisStruct, Generic[a]):
    pass


@namespace.function(type_vars={"a": StarKind()})
async def discard(value: a) -> EmptyOut[a]:
    """Deletes its input value."""
    # things won't actually be deleted until python decides to
    return EmptyOut()


@dataclass
class EqOut(TierkreisStruct, Generic[a]):
    result: bool


@namespace.function(type_vars={"val": StarKind()})
async def eq(value_0: val, value_1: val) -> EqOut:
    """Check two values for equality."""
    return EqOut(value_0 == value_1)


async def _eval(_x: StructValue) -> StructValue:
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
        description="Evaluates a graph.",
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
    # pylint: disable=redefined-builtin
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
    """Passes on an arbitrary value unchanged."""
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


async def _insert_key(ins: StructValue) -> StructValue:
    # Extract the arguments to the operation
    inner_map = cast(MapValue, ins.values["map"])
    key = ins.values["key"]
    val = ins.values["val"]

    # Perform update (destructively is fine)
    inner_map.values[key] = val
    return StructValue({"map": inner_map})


namespace.functions["insert_key"] = Function(
    run=_insert_key,
    declaration=FunctionDeclaration(
        type_scheme=TypeScheme(
            variables=[
                TypeSchemeVar(name="key", kind=Kind(star=Empty())),
                TypeSchemeVar(name="val", kind=Kind(star=Empty())),
            ],
            body=Type(
                graph=GraphType(
                    inputs=RowType(
                        content={
                            "map": Type(
                                map=PairType(
                                    first=Type(var="key"), second=Type(var="val")
                                )
                            ),
                            "val": Type(var="val"),
                            "key": Type(var="key"),
                        }
                    ),
                    outputs=RowType(
                        content={
                            "map": Type(
                                map=PairType(
                                    first=Type(var="key"), second=Type(var="val")
                                )
                            )
                        }
                    ),
                )
            ),
        ),
        description="Insert a key value pair in to a map."
        " Existing keys will have their values replaced.",
        input_order=["map", "key", "val"],
        output_order=["map"],
    ),
)


@namespace.function()
async def int_to_float(int: int) -> float:
    # pylint: disable=redefined-builtin
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


async def _loop(_x: StructValue) -> StructValue:
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
        description="Run a looping thunk while it returns"
        " `continue` i.e. until it returns `break`.",
        input_order=["body", "value"],
        output_order=["value"],
    ),
)


@dataclass
class _MakePairOut(TierkreisStruct, Generic[a, b]):
    pair: tuple[a, b]


@namespace.function(type_vars={"a": StarKind(), "b": StarKind()})
async def make_pair(first: a, second: b) -> _MakePairOut[a, b]:
    "Creates a new pair."
    return _MakePairOut((first, second))


async def make_struct(ins: StructValue) -> StructValue:
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
        description="Construct a struct from incoming ports.",
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


async def _partial(inputs: StructValue) -> StructValue:
    invals = inputs.values
    thunk = deepcopy(cast(GraphValue, invals.pop("thunk")).value)
    newg = TierkreisGraph()
    rest_inputs = [port for port in thunk.inputs() if port not in invals]
    inports = map_vals(invals, lambda x: newg.add_const(x)["value"])
    inports.update({port: newg.input[port] for port in rest_inputs})
    box = newg.add_box(thunk, **inports)
    newg.set_outputs(**{port: box[port] for port in thunk.outputs()})
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
class _PopOut(TierkreisStruct, Generic[a]):
    vec: list[a]
    item: a


@namespace.function(type_vars={"a": StarKind()})
async def pop(vec: list[a]) -> _PopOut[a]:
    """Split the last item from a Vec."""
    item = vec.pop()
    return _PopOut(vec, item)


@dataclass
class _PushOut(TierkreisStruct, Generic[a]):
    vec: list[a]


@namespace.function(type_vars={"a": StarKind()})
async def push(vec: list[a], item: a) -> _PushOut[a]:
    """Push an item on to end of a Vec."""
    vec.append(item)
    return _PushOut(vec)


async def _remove_key(ins: StructValue) -> StructValue:
    inner_map = cast(MapValue, ins.values["map"])
    val = inner_map.values.pop(ins.values["key"])

    return StructValue({"map": inner_map, "val": val})


namespace.functions["remove_key"] = Function(
    run=_remove_key,
    declaration=FunctionDeclaration(
        type_scheme=TypeScheme(
            variables=[
                TypeSchemeVar(name="key", kind=Kind(star=Empty())),
                TypeSchemeVar(name="val", kind=Kind(star=Empty())),
            ],
            body=Type(
                graph=GraphType(
                    inputs=RowType(
                        content={
                            "key": Type(var="key"),
                            "map": Type(
                                map=PairType(
                                    first=Type(var="key"), second=Type(var="val")
                                )
                            ),
                        }
                    ),
                    outputs=RowType(
                        content={
                            "val": Type(var="val"),
                            "map": Type(
                                map=PairType(
                                    first=Type(var="key"), second=Type(var="val")
                                )
                            ),
                        }
                    ),
                )
            ),
        ),
        description="Remove a key value pair from a map and return the map and value.",
        input_order=["map", "key"],
        output_order=["map", "val"],
    ),
)


async def _sequence(inputs: StructValue) -> StructValue:
    invals = cast(dict[str, IncomingWireType], inputs.values)
    first = deepcopy(cast(GraphValue, invals.pop("first")).value)
    second = deepcopy(cast(GraphValue, invals.pop("second")).value)
    newg = TierkreisGraph()
    box1 = newg.add_box(first, **{port: newg.input[port] for port in first.inputs()})
    box2 = newg.add_box(second, **{port: box1[port] for port in first.outputs()})
    newg.set_outputs(**{port: box2[port] for port in second.outputs()})
    return StructValue({"sequenced": GraphValue(newg.inline_boxes())})


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


async def _parallel(inputs: StructValue) -> StructValue:
    invals = inputs.values
    left = deepcopy(cast(GraphValue, invals.pop("left")).value)
    right = deepcopy(cast(GraphValue, invals.pop("right")).value)
    newg = TierkreisGraph()
    box1 = newg.add_box(left, **{port: newg.input[port] for port in left.inputs()})
    box2 = newg.add_box(right, **{port: newg.input[port] for port in right.inputs()})
    outputs = dict(
        {port: box1[port] for port in left.outputs()},
        **{port: box2[port] for port in right.outputs()}
    )
    newg.set_outputs(**outputs)
    return StructValue({"value": GraphValue(newg.inline_boxes())})


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
        description="Compose two graphs in parallel.",
        input_order=["left", "right"],
        output_order=["value"],
    ),
)


@namespace.function(type_vars={"a": StarKind()})
async def switch(pred: bool, if_true: a, if_false: a) -> a:
    """Chooses a value depending on a boolean predicate."""
    return if_true if pred else if_false


@dataclass
class _UnpackPairOut(TierkreisStruct, Generic[a, b]):
    first: a
    second: b


@namespace.function(type_vars={"a": StarKind(), "b": StarKind()})
async def unpack_pair(pair: tuple[a, b]) -> _UnpackPairOut[a, b]:
    "Unpacks a pair."
    return _UnpackPairOut(*pair)


async def _unpack_struct(ins: StructValue) -> StructValue:
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
        description="Destructure a struct in to outgoing ports.",
        input_order=["struct"],
    ),
)


@namespace.function()
async def xor(a: bool, b: bool) -> bool:
    """Check either a or b are true; a ^ b"""
    return a ^ b
