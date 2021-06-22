from abc import ABC, abstractmethod
import typing
from dataclasses import dataclass, field
import tierkreis.core.protos.tierkreis.graph as pg
from pytket.circuit import Circuit  # type: ignore
from typing import Dict, List, Optional, cast
from tierkreis.core.internal import python_struct_fields
from tierkreis.core.tierkreis_struct import TierkreisStruct
import betterproto


class TierkreisType(ABC):
    @abstractmethod
    def to_proto(self) -> pg.Type:
        "Converts a tierkreis type to its protobuf representation."
        pass

    @staticmethod
    def from_python(type_: typing.Type) -> "TierkreisType":
        "Converts a python type to its corresponding tierkreis type."

        from tierkreis.core.python import RuntimeGraph

        type_origin = typing.get_origin(type_)

        # TODO: Graph types

        if type_ is int:
            return IntType()
        elif type_ is bool:
            return BoolType()
        elif type_ is str:
            return StringType()
        elif type_ is float:
            return FloatType()
        elif type_origin is list:
            args = typing.get_args(type_)
            return ArrayType(element=TierkreisType.from_python(args[0]))
        elif type_origin is tuple:
            args = typing.get_args(type_)
            return PairType(
                first=TierkreisType.from_python(args[0]),
                second=TierkreisType.from_python(args[1]),
            )
        elif type_origin is dict:
            args = typing.get_args(type_)
            return MapType(
                key=TierkreisType.from_python(args[0]),
                value=TierkreisType.from_python(args[1]),
            )
        elif type_ is Circuit:
            return CircuitType()
        elif isinstance(type_, typing.TypeVar):
            return VarType(name=type_.__name__)
        elif type_origin is RuntimeGraph:
            args = typing.get_args(type_)
            return GraphType(
                inputs=Row.from_python(args[0]), outputs=Row.from_python(args[1])
            )
        elif type_origin is None and TierkreisStruct in type_.__bases__:
            return StructType(shape=Row.from_python(type_))
        elif type_origin is not None and TierkreisStruct in type_origin.__bases__:
            return StructType(shape=Row.from_python(type_))
        else:
            raise ValueError(
                f"Could not convert python type to tierkreis type: {type_}"
            )

    @staticmethod
    def from_proto(type_: pg.Type) -> "TierkreisType":
        name, out_type = betterproto.which_one_of(type_, "type")

        if name == "int":
            return IntType()
        elif name == "bool":
            return BoolType()
        elif name == "str_":
            return StringType()
        elif name == "flt":
            return FloatType()
        elif name == "circuit":
            return CircuitType()
        elif name == "var":
            return VarType(cast(str, out_type))
        elif name == "pair":
            pair_type = cast(pg.PairType, out_type)
            first = TierkreisType.from_proto(pair_type.first)
            second = TierkreisType.from_proto(pair_type.second)
            return PairType(first, second)
        elif name == "array":
            element = TierkreisType.from_proto(cast(pg.Type, out_type))
            return ArrayType(element)
        elif name == "struct":
            row = cast(pg.RowType, out_type)
            return StructType(Row.from_proto(row))
        elif name == "map":
            map_type = cast(pg.PairType, out_type)
            key = TierkreisType.from_proto(map_type.first)
            value = TierkreisType.from_proto(map_type.second)
            return MapType(key, value)
        elif name == "graph":
            graph_type = cast(pg.GraphType, out_type)
            inputs = Row.from_proto(graph_type.inputs)
            outputs = Row.from_proto(graph_type.outputs)
            return GraphType(inputs, outputs)
        else:
            raise ValueError(f"Unknown protobuf type: {name}")


@dataclass
class IntType(TierkreisType):
    def to_proto(self) -> pg.Type:
        return pg.Type(int=pg.Empty())


@dataclass
class BoolType(TierkreisType):
    def to_proto(self) -> pg.Type:
        return pg.Type(bool=pg.Empty())


@dataclass
class StringType(TierkreisType):
    def to_proto(self) -> pg.Type:
        return pg.Type(str_=pg.Empty())


@dataclass
class FloatType(TierkreisType):
    def to_proto(self) -> pg.Type:
        return pg.Type(flt=pg.Empty())


@dataclass
class CircuitType(TierkreisType):
    def to_proto(self) -> pg.Type:
        return pg.Type(circuit=pg.Empty())


@dataclass
class VarType(TierkreisType):
    name: str

    def to_proto(self) -> pg.Type:
        return pg.Type(var=self.name)


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


@dataclass
class ArrayType(TierkreisType):
    element: TierkreisType

    def to_proto(self) -> pg.Type:
        return pg.Type(array=self.element.to_proto())


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


@dataclass
class Row:
    content: Dict[str, TierkreisType] = field(default_factory=dict)
    rest: Optional[str] = None

    def to_proto(self) -> pg.RowType:
        return pg.RowType(
            content={label: type_.to_proto() for label, type_ in self.content.items()},
            rest=self.rest or "",
        )

    @staticmethod
    def from_python(type_: typing.Type) -> "Row":
        if isinstance(type_, typing.TypeVar):
            return Row(rest=type_.__name__)
        else:
            return Row(
                content={
                    field_name: TierkreisType.from_python(field_type)
                    for field_name, field_type in python_struct_fields(type_).items()
                }
            )

    @staticmethod
    def from_proto(row: pg.RowType) -> "Row":
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


@dataclass
class GraphType(TierkreisType):
    inputs: Row
    outputs: Row

    def to_proto(self) -> pg.Type:
        return pg.Type(
            graph=pg.GraphType(
                inputs=self.inputs.to_proto(),
                outputs=self.outputs.to_proto(),
            )
        )


@dataclass
class StructType(TierkreisType):
    shape: Row

    def to_proto(self) -> pg.Type:
        return pg.Type(struct=self.shape.to_proto())


class Constraint(ABC):
    @abstractmethod
    def to_proto(self) -> pg.Constraint:
        pass

    @classmethod
    def from_proto(cls, pg_const: pg.Constraint) -> "Constraint":
        return cls()


class Kind(ABC):
    @abstractmethod
    def to_proto(self) -> pg.Kind:
        pass

    @classmethod
    def from_proto(cls, proto_kind: pg.Kind) -> "Kind":
        name, _ = betterproto.which_one_of(proto_kind, "kind")
        if "name" == "row":
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
    variables: Dict[str, Kind]
    constraints: List[Constraint]
    body: GraphType

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
    def from_proto(cls, proto_tg: pg.TypeScheme) -> "TypeSchema":
        variables = {ts_var.name: Kind.from_proto(ts_var.kind) for ts_var in proto_tg.variables}
        constraints = [Constraint.from_proto(pg_const) for pg_const in proto_tg.constraints]
        body = TierkreisType.from_proto(proto_tg.body)
        # g_type = proto_tg.body.graph

        # inputs = Row.from_proto(g_type.inputs)
        # outputs = Row.from_proto(g_type.outputs)
        return cls(variables, constraints, body)