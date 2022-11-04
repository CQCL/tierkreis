import typing
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, is_dataclass
from functools import reduce
from typing import Optional, cast
from uuid import UUID

import betterproto

import tierkreis.core.protos.tierkreis.v1alpha.graph as pg
from tierkreis.core.internal import python_struct_fields
from tierkreis.core.tierkreis_struct import TierkreisStruct

from . import Labels

# import from types when updating to python 3.10
try:
    from types import NoneType  # type: ignore
except ImportError as _:
    NoneType = type(None)


def _get_optional_type(type_: typing.Type) -> typing.Optional[typing.Type]:
    args = typing.get_args(type_)
    if typing.get_origin(type_) is typing.Union and NoneType in args:
        return args[0]
    return None


class TierkreisType(ABC):
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
        elif inner_type := _get_optional_type(type_):
            inner = TierkreisType.from_python(inner_type, visited_types)
            result = VariantType(
                shape=Row(
                    content={Labels.NONE: StructType(shape=Row()), Labels.SOME: inner}
                )
            )
        elif type_origin is list:
            args = typing.get_args(type_)
            result = VecType(element=TierkreisType.from_python(args[0], visited_types))
        elif type_origin is tuple:
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
        elif (TierkreisStruct in type_.__bases__) or is_dataclass(type_):
            actual_type = type_origin or type_
            result = StructType(
                shape=Row.from_python(actual_type, visited_types), name=type_name
            )
        elif type_ is UUID:
            result = StringType()
        else:
            raise ValueError(
                f"Could not convert python type to tierkreis type: {type_}"
            )

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

    @staticmethod
    def from_python(
        type_: typing.Type,
        visited_types: typing.Optional[dict[typing.Type, "TierkreisType"]] = None,
    ) -> "Row":
        if isinstance(type_, typing.TypeVar):
            return Row(rest=type_.__name__)
        else:

            return Row(
                content={
                    field_name: TierkreisType.from_python(field_type, visited_types)
                    for field_name, field_type in python_struct_fields(type_).items()
                }
            )

    @staticmethod
    def from_proto(row_type: pg.Type) -> "Row":
        return Row.from_proto_rowtype(row_type.row)

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
