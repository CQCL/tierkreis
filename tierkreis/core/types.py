import inspect
import typing
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from functools import reduce
from types import NoneType, UnionType
from typing import Any, ClassVar, Generic, Iterable, Optional, Protocol, TypeVar, cast
from uuid import UUID

import betterproto
from typing_extensions import Self

import tierkreis.core.protos.tierkreis.v1alpha1.graph as pg
from tierkreis.core.internal import python_struct_fields
from tierkreis.core.opaque_model import _to_snake_case


def _get_union_args(
    type_: typing.Type,
) -> typing.Optional[typing.Tuple[typing.Type, ...]]:
    # "Union" syntax or "A | B" syntax produces different results
    if type(type_) is UnionType or typing.get_origin(type_) is typing.Union:
        return typing.get_args(type_)
    return None


def _extract_literal_args(type_: typing.Type) -> Optional[tuple]:
    if typing.get_origin(type_) is typing.Literal:
        return typing.get_args(type_)
    return None


def _extract_literal_type(type_: typing.Type) -> Optional[typing.Type]:
    if args := _extract_literal_args(type_):
        # all args of literal must be the same type
        return type(args[0])
    return None


def _is_enum(type_: typing.Type) -> Optional[typing.Type[Enum]]:
    if inspect.isclass(type_) and issubclass(type_, Enum):
        return type_
    return None


def _is_annotated(type_: typing.Type) -> Optional[typing.Type]:
    if typing.get_origin(type_) is typing.Annotated:
        return typing.get_args(type_)[0]
    return None


def _is_var_length_tuple(args: tuple) -> Optional[typing.Type]:
    if len(args) == 2 and args[1] == ...:
        return args[0]
    return None


Base = TypeVar("Base")


class SerializeAs(Protocol[Base]):
    """Methods implemented by Tierkreis-compatible types used as alternatives to
    Base"""

    @classmethod
    def new_tierkreis_compatible(cls, value: Base) -> Self:
        """Create a new instance of the tierkreis-compatible type from a Base instance."""
        ...

    def from_tierkreis_compatible(self) -> Base:
        """Convert the tierkreis-compatible type to a Base instance."""
        ...


@dataclass
class IncompatiblePyType(Exception):
    type_: Any

    def __str__(self) -> str:
        return f"Could not convert python type to tierkreis type: {self.type_}"


class TierkreisType(ABC):
    _convert_as: dict[typing.Type, typing.Type[SerializeAs]] = dict()

    @abstractmethod
    def to_proto(self) -> pg.Type:
        "Converts a tierkreis type to its protobuf representation."

    @classmethod
    def from_python(
        cls,
        type_: typing.Type,
        visited_types: typing.Optional[dict[typing.Type, "TierkreisType"]] = None,
    ) -> "TierkreisType":
        "Converts a python type to its corresponding tierkreis type."

        if alternative := TierkreisType._convert_as.get(type_):
            return TierkreisType.from_python(alternative, visited_types)
        from tierkreis.core.python import RuntimeGraph

        visited_types = visited_types or {}

        if type_ in visited_types:
            seen = visited_types[type_]
            return seen

        try:
            type_name = type_.__name__
        except AttributeError as _e:
            type_name = str(type_)

        visited_types[type_] = VarType(f"CyclicType_{type_name}")
        type_origin = typing.get_origin(type_)
        result: TierkreisType
        # TODO: Graph types
        if type_ is int:
            result = IntType()
        elif type_ is bool:
            result = BoolType()
        elif type_ is str:
            result = StringType()
        elif type_ is float:
            result = FloatType()
        elif type_ is NoneType:
            result = UNIT_TYPE
        elif type_origin is list:
            args = typing.get_args(type_)
            result = VecType(element=TierkreisType.from_python(args[0], visited_types))
        elif type_origin is tuple:
            args = typing.get_args(type_)
            if element_type := _is_var_length_tuple(args):
                # Varargs tuple can be treated as list
                result = VecType(TierkreisType.from_python(element_type, visited_types))
            else:
                result = StructType.from_tuple(args, visited_types)
        elif type_origin is TierkreisPair:
            args = typing.get_args(type_)
            result = PairType(
                first=TierkreisType.from_python(args[0], visited_types),
                second=TierkreisType.from_python(args[1], visited_types),
            )
        elif type_origin is dict:
            args = typing.get_args(type_)
            result = MapType(
                key=TierkreisType.from_python(args[0], visited_types),
                value=TierkreisType.from_python(args[1], visited_types),
            )

        elif isinstance(type_, typing.TypeVar):
            result = VarType(name=type_.__name__)
        elif type_origin is RuntimeGraph:
            args = typing.get_args(type_)
            result = GraphType(
                inputs=Row.from_python(args[0], visited_types),
                outputs=Row.from_python(args[1], visited_types),
            )
        elif type_ is UUID:
            result = StringType()

        elif enum_type := _is_enum(type_):
            result = VariantType(Row({x.name: UNIT_TYPE for x in enum_type}))

        elif union_args := _get_union_args(type_):
            variants = {
                UnionTag.type_tag(t): TierkreisType.from_python(t, visited_types)
                for t in union_args
            }
            if len(set(variants.keys())) != len(union_args):
                raise ValueError(
                    "Could not generate unique names for all possible union types."
                    " For example a list[int] and list[float] would both generate the tag '__py_union_list'."
                    "Try using a discrimnated field in a dataclass instead."
                )
            result = VariantType(shape=Row(content=variants))
        elif inner_type := _extract_literal_type(type_):
            return cls.from_python(inner_type)
        elif inner_type := _is_annotated(type_):
            return cls.from_python(inner_type)
        elif inspect.isclass(type_):
            actual_type = cast(typing.Type, type_origin or type_)
            result = StructType(
                shape=Row.from_python(actual_type, visited_types), name=type_name
            )
        else:
            raise IncompatiblePyType(type_)

        visited_types[type_] = result

        if not isinstance(result, cls):
            raise TypeError()

        return result

    @classmethod
    def from_proto(cls, type_: pg.Type) -> "TierkreisType":
        name, out_type = betterproto.which_one_of(type_, "type")

        result: TierkreisType

        if name == "int":
            result = IntType()
        elif name == "bool":
            result = BoolType()
        elif name == "str":
            result = StringType()
        elif name == "flt":
            result = FloatType()
        elif name == "var":
            result = VarType(cast(str, out_type))
        elif name == "pair":
            pair_type = cast(pg.PairType, out_type)
            first = TierkreisType.from_proto(pair_type.first)
            second = TierkreisType.from_proto(pair_type.second)
            result = PairType(first, second)
        elif name == "vec":
            element = TierkreisType.from_proto(cast(pg.Type, out_type))
            result = VecType(element)
        elif name == "struct":
            struct_type = cast(pg.StructType, out_type)
            result = StructType(
                Row.from_proto_rowtype(struct_type.shape), struct_type.name or None
            )
        elif name == "map":
            map_type = cast(pg.PairType, out_type)
            key = TierkreisType.from_proto(map_type.first)
            value = TierkreisType.from_proto(map_type.second)
            result = MapType(key, value)
        elif name == "graph":
            graph_type = cast(pg.GraphType, out_type)
            inputs = Row.from_proto_rowtype(graph_type.inputs)
            outputs = Row.from_proto_rowtype(graph_type.outputs)
            result = GraphType(inputs, outputs)
        elif name == "variant":
            shape = cast(pg.RowType, out_type)
            result = VariantType(Row.from_proto_rowtype(shape))
        else:
            raise ValueError(f"Unknown protobuf type: {name}")

        if not isinstance(result, cls):
            raise TypeError()

        return result

    def children(self) -> list["TierkreisType"]:
        return []

    def contained_vartypes(self) -> set[str]:
        return reduce(
            lambda x, y: x.union(y),
            (child.contained_vartypes() for child in self.children()),
            set(),
        )

    @classmethod
    def register_alternative(
        cls, type_: typing.Type, alternative: typing.Type[SerializeAs]
    ):
        """Register an alternative type that can be used to convert to/from TierkreisType."""
        cls._convert_as[type_] = alternative


@dataclass
class IntType(TierkreisType):
    def to_proto(self) -> pg.Type:
        return pg.Type(int=pg.Empty())

    def __str__(self) -> str:
        return "Int"


@dataclass
class BoolType(TierkreisType):
    def to_proto(self) -> pg.Type:
        return pg.Type(bool=pg.Empty())

    def __str__(self) -> str:
        return "Bool"


@dataclass
class StringType(TierkreisType):
    def to_proto(self) -> pg.Type:
        return pg.Type(str=pg.Empty())

    def __str__(self) -> str:
        return "Str"


@dataclass
class FloatType(TierkreisType):
    def to_proto(self) -> pg.Type:
        return pg.Type(flt=pg.Empty())

    def __str__(self) -> str:
        return "Float"


@dataclass
class VarType(TierkreisType):
    name: str

    def to_proto(self) -> pg.Type:
        return pg.Type(var=self.name)

    def __str__(self) -> str:
        return f"VarType({self.name})"

    def contained_vartypes(self) -> set[str]:
        return {self.name}


First = TypeVar("First")
Second = TypeVar("Second")


@dataclass(frozen=True)
class TierkreisPair(Generic[First, Second]):
    """A pair of values that can be converted to/from a Tierkreis Pair type."""

    first: First
    second: Second


@dataclass
class PairType(TierkreisType):
    first: TierkreisType
    second: TierkreisType

    def to_proto(self) -> pg.Type:
        return pg.Type(
            pair=pg.PairType(
                first=self.first.to_proto(),
                second=self.second.to_proto(),
            )
        )

    def __str__(self) -> str:
        return f"Pair[{str(self.first)}, {str(self.second)}]"

    def children(self) -> list["TierkreisType"]:
        return [self.first, self.second]


@dataclass
class VecType(TierkreisType):
    element: TierkreisType

    def to_proto(self) -> pg.Type:
        return pg.Type(vec=self.element.to_proto())

    def __str__(self) -> str:
        return f"Vector[{str(self.element)}]"

    def children(self) -> list["TierkreisType"]:
        return [self.element]


@dataclass
class MapType(TierkreisType):
    key: TierkreisType
    value: TierkreisType

    def to_proto(self) -> pg.Type:
        return pg.Type(
            map=pg.PairType(
                first=self.key.to_proto(),
                second=self.value.to_proto(),
            )
        )

    def __str__(self) -> str:
        return f"Map[{str(self.key)}, {str(self.value)}]"

    def children(self) -> list["TierkreisType"]:
        return [self.key, self.value]


class UnpackRow:
    "Base class to tag dataclasses with to indicate they should be unpacked in to a row."


@dataclass
class Row(TierkreisType):
    content: dict[str, TierkreisType] = field(default_factory=dict)
    rest: typing.Optional[str] = None

    def to_proto(self) -> pg.Type:
        return pg.Type(
            row=pg.RowType(
                content={
                    label: type_.to_proto() for label, type_ in self.content.items()
                },
                rest=self.rest or "",
            )
        )

    @classmethod
    def from_python(
        cls,
        type_: typing.Type,
        visited_types: typing.Optional[dict[typing.Type, "TierkreisType"]] = None,
    ) -> "Row":
        if isinstance(type_, typing.TypeVar):
            return Row(rest=type_.__name__)

        try:
            class_fields = python_struct_fields(type_)
        except ValueError as e:
            raise IncompatiblePyType(type_) from e
        return Row(
            content={
                field.name: _from_disc_field(
                    field.type_,
                    field.discriminant,
                    visited_types,
                )
                for field in class_fields
            }
        )

    @classmethod
    def from_proto(cls, type_: pg.Type) -> "Row":
        return Row.from_proto_rowtype(type_.row)

    @staticmethod
    def from_proto_rowtype(row: pg.RowType) -> "Row":
        if row.rest == "":
            rest = None
        else:
            rest = row.rest

        return Row(
            content={
                field_name: TierkreisType.from_proto(field_type)
                for field_name, field_type in row.content.items()
            },
            rest=rest,
        )

    def to_tksl(self) -> str:
        contentstr = ", ".join(
            (f"{key}: {str(val)}" for key, val in sorted(self.content.items()))
        )
        reststr = f", #: {self.rest}" if self.rest else ""

        return f"{contentstr}{reststr}"

    def children(self) -> list["TierkreisType"]:
        return list(self.content.values())


@dataclass
class GraphType(TierkreisType):
    inputs: Row
    outputs: Row

    def to_proto(self) -> pg.Type:
        return pg.Type(
            graph=pg.GraphType(
                inputs=self.inputs.to_proto().row,
                outputs=self.outputs.to_proto().row,
            )
        )

    def __str__(self) -> str:
        return f"({self.inputs.to_tksl()}) -> ({self.outputs.to_tksl()})"

    def children(self) -> list["TierkreisType"]:
        return self.inputs.children() + self.outputs.children()


@dataclass
class StructType(TierkreisType):
    shape: Row
    name: Optional[str] = None

    def to_proto(self) -> pg.Type:
        row = self.shape.to_proto().row
        struct_type = pg.StructType(row, self.name) if self.name else pg.StructType(row)
        return pg.Type(struct=struct_type)

    def anon_name(self) -> str:
        return f"Struct[{self.shape.to_tksl()}]"

    def __str__(self) -> str:
        return self.name or self.anon_name()

    def children(self) -> list["TierkreisType"]:
        return self.shape.children()

    @classmethod
    def from_python(
        cls,
        type_: typing.Type,
        visited_types: typing.Optional[dict[typing.Type, "TierkreisType"]] = None,
    ) -> "StructType":
        return StructType(Row.from_python(type_, visited_types))

    @classmethod
    def from_tuple(
        cls,
        args: Iterable[typing.Type],
        visited_types: typing.Optional[dict[typing.Type, "TierkreisType"]] = None,
    ) -> "StructType":
        return StructType(
            shape=Row(
                {
                    TupleLabel.index_label(i): TierkreisType.from_python(
                        t, visited_types
                    )
                    for i, t in enumerate(args)
                },
            ),
        )


@dataclass
class VariantType(TierkreisType):
    shape: Row

    def to_proto(self) -> pg.Type:
        row = self.shape.to_proto().row
        return pg.Type(variant=row)

    def __str__(self) -> str:
        return f"Variant[{self.shape.to_tksl()}]"

    def children(self) -> list["TierkreisType"]:
        return self.shape.children()


@dataclass(frozen=True)
class UnionTag:
    prefix: ClassVar[str] = "__py_union_"

    @dataclass
    class UnexpectedTag(Exception):
        tag: str

    @staticmethod
    def parse_type(s: str, types: Iterable[typing.Type]) -> typing.Type:
        if not s.startswith(UnionTag.prefix):
            raise UnionTag.UnexpectedTag(s)
        # will raise StopIteration if the substring does not match the __name__
        # of any type in args
        return next(t for t in types if UnionTag.type_tag(t) == s)

    @staticmethod
    def type_tag(type_: typing.Type) -> str:
        # convert names to snake case to avoid mismatch between `list` vs.
        # `List` etc.

        return UnionTag.prefix + _to_snake_case(type_.__name__)

    @staticmethod
    def value_type_tag(value: Any) -> str:
        return UnionTag.type_tag(type(value))

    @classmethod
    def none_type_tag(cls) -> str:
        return UnionTag.type_tag(NoneType)


@dataclass(frozen=True)
class TupleLabel:
    """Generate and parse struct field labels for tuple members."""

    prefix: ClassVar[str] = "__py_tuple_"

    @dataclass
    class UnexpectedLabel(Exception):
        """The label does not conform to tuple member format"""

        label: str

    @staticmethod
    def index_label(idx: int) -> str:
        """Generate a label for a tuple member at position `idx`"""
        return f"{TupleLabel.prefix}{idx}"

    @staticmethod
    def parse_label(s: str) -> int:
        """Parse a tuple member index from a label string."""
        if not s.startswith(TupleLabel.prefix):
            raise TupleLabel.UnexpectedLabel(s)
        s = s[len(TupleLabel.prefix) :]
        try:
            return int(s)
        except ValueError as e:
            raise TupleLabel.UnexpectedLabel(s) from e


class Constraint(ABC):
    @abstractmethod
    def to_proto(self) -> pg.Constraint:
        pass

    @classmethod
    def from_proto(cls, pg_const: pg.Constraint) -> "Constraint":
        name, _ = betterproto.which_one_of(pg_const, "constraint")

        if name == "lacks":
            lacks = pg_const.lacks
            return LacksConstraint(
                row=TierkreisType.from_proto(lacks.row), label=lacks.label
            )
        elif name == "partition":
            partition = pg_const.partition
            return PartitionConstraint(
                left=TierkreisType.from_proto(partition.left),
                right=TierkreisType.from_proto(partition.right),
                union=TierkreisType.from_proto(partition.union),
            )
        else:
            raise ValueError(f"Unknown constraint type: {name}")


@dataclass
class LacksConstraint(Constraint):
    row: TierkreisType
    label: str

    def to_proto(self) -> pg.Constraint:
        return pg.Constraint(
            lacks=pg.LacksConstraint(row=self.row.to_proto(), label=self.label)
        )


@dataclass
class PartitionConstraint(Constraint):
    left: TierkreisType
    right: TierkreisType
    union: TierkreisType

    def to_proto(self) -> pg.Constraint:
        return pg.Constraint(
            partition=pg.PartitionConstraint(
                left=self.left.to_proto(),
                right=self.right.to_proto(),
                union=self.union.to_proto(),
            )
        )


class Kind(ABC):
    @abstractmethod
    def to_proto(self) -> pg.Kind:
        pass

    @classmethod
    def from_proto(cls, proto_kind: pg.Kind) -> "Kind":
        name, _ = betterproto.which_one_of(proto_kind, "kind")
        if name == "row":
            return RowKind()
        return StarKind()


@dataclass
class StarKind(Kind):
    def to_proto(self) -> pg.Kind:
        return pg.Kind(star=pg.Empty())


@dataclass
class RowKind(Kind):
    def to_proto(self) -> pg.Kind:
        return pg.Kind(row=pg.Empty())


@dataclass
class TypeScheme:
    variables: dict[str, Kind]
    constraints: list[Constraint]
    body: TierkreisType

    def to_proto(self) -> pg.TypeScheme:
        return pg.TypeScheme(
            variables=[
                pg.TypeSchemeVar(name=name, kind=kind.to_proto())
                for name, kind in self.variables.items()
            ],
            constraints=[constraint.to_proto() for constraint in self.constraints],
            body=self.body.to_proto(),
        )

    @classmethod
    def from_proto(cls, proto_tg: pg.TypeScheme) -> "TypeScheme":
        variables = {
            ts_var.name: Kind.from_proto(ts_var.kind) for ts_var in proto_tg.variables
        }
        constraints = [
            Constraint.from_proto(pg_const) for pg_const in proto_tg.constraints
        ]
        body = TierkreisType.from_proto(proto_tg.body)
        return cls(variables, constraints, body)


UNIT_TYPE = StructType(Row())


def _get_discriminators(
    field_type: typing.Type,
    disc: Optional[str],
) -> Optional[dict[str, typing.Type]]:
    """If a dataclass field is a discriminated union find the map from tag name
    to variant type."""
    union_args = _get_union_args(field_type)
    if disc is None or union_args is None:
        return None

    var_row = {}
    for t in union_args:
        if args := _extract_literal_args(typing.get_type_hints(t)[disc]):
            assert isinstance(args[0], str)
            var_row[args[0]] = t

    return var_row


def _from_disc_field(
    field_type: typing.Type,
    disc: Optional[str],
    visited_types: Optional[dict[typing.Type, TierkreisType]],
) -> TierkreisType:
    """If a dataclass field is a discriminated union, map it to a variant type,
    else compute it's type normally."""
    var_row = _get_discriminators(field_type, disc)
    if var_row is None:
        return TierkreisType.from_python(field_type, visited_types)

    return VariantType(
        Row({k: TierkreisType.from_python(v) for k, v in var_row.items()})
    )
