import typing
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, cast

import betterproto

import tierkreis.core.protos.tierkreis.graph as pg
import tierkreis.core.protos.tierkreis.signature as ps
from tierkreis.core.internal import python_struct_fields
from tierkreis.core.tierkreis_struct import TierkreisStruct

# import from types when updating to python 3.10
NoneType = type(None)


class TierkreisType(ABC):
    @abstractmethod
    def to_proto(self) -> pg.Type:
        "Converts a tierkreis type to its protobuf representation."

    @classmethod
    def from_python(cls, type_: typing.Type) -> "TierkreisType":
        "Converts a python type to its corresponding tierkreis type."

        from tierkreis.core.python import RuntimeGraph

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
            result = UnitType()
        elif type_origin is list:
            args = typing.get_args(type_)
            result = VecType(element=TierkreisType.from_python(args[0]))
        elif type_origin is tuple:
            args = typing.get_args(type_)
            result = PairType(
                first=TierkreisType.from_python(args[0]),
                second=TierkreisType.from_python(args[1]),
            )
        elif type_origin is dict:
            args = typing.get_args(type_)
            result = MapType(
                key=TierkreisType.from_python(args[0]),
                value=TierkreisType.from_python(args[1]),
            )

        elif isinstance(type_, typing.TypeVar):
            result = VarType(name=type_.__name__)
        elif type_origin is RuntimeGraph:
            args = typing.get_args(type_)
            result = GraphType(
                inputs=Row.from_python(args[0]), outputs=Row.from_python(args[1])
            )
        elif type_origin is None and TierkreisStruct in type_.__bases__:
            result = StructType(shape=Row.from_python(type_))
        elif type_origin is not None and TierkreisStruct in type_origin.__bases__:
            result = StructType(shape=Row.from_python(type_))
        else:
            raise ValueError(
                f"Could not convert python type to tierkreis type: {type_}"
            )

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
        elif name == "str_":
            result = StringType()
        elif name == "flt":
            result = FloatType()
        elif name == "unit":
            result = UnitType()
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
            row = cast(pg.RowType, out_type)
            result = StructType(Row.from_proto(row))
        elif name == "map":
            map_type = cast(pg.PairType, out_type)
            key = TierkreisType.from_proto(map_type.first)
            value = TierkreisType.from_proto(map_type.second)
            result = MapType(key, value)
        elif name == "graph":
            graph_type = cast(pg.GraphType, out_type)
            inputs = Row.from_proto(graph_type.inputs)
            outputs = Row.from_proto(graph_type.outputs)
            result = GraphType(inputs, outputs)
        else:
            raise ValueError(f"Unknown protobuf type: {name}")

        if not isinstance(result, cls):
            raise TypeError()

        return result


@dataclass
class UnitType(TierkreisType):
    def to_proto(self) -> pg.Type:
        return pg.Type(unit=pg.Empty())

    def __str__(self) -> str:
        return "Unit"


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
        return pg.Type(str_=pg.Empty())

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
        return f"Pair<{str(self.first)}, {str(self.second)}>"


@dataclass
class VecType(TierkreisType):
    element: TierkreisType

    def to_proto(self) -> pg.Type:
        return pg.Type(vec=self.element.to_proto())

    def __str__(self) -> str:
        return f"Vector<{str(self.element)}>"


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
        return f"Map<{str(self.key)}, {str(self.value)}>"


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

    def to_tksl(self) -> str:
        contentstr = ", ".join(
            (f"{key}: {str(val)}" for key, val in self.content.items())
        )
        reststr = f", #: {self.rest}" if self.rest else ""

        return f"{contentstr}{reststr}"


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

    def __str__(self) -> str:
        return f"Graph ({self.inputs.to_tksl()}) -> ({self.outputs.to_tksl()})"


@dataclass
class StructType(TierkreisType):
    shape: Row

    def to_proto(self) -> pg.Type:
        return pg.Type(struct=self.shape.to_proto())

    def __str__(self) -> str:
        return f"Struct<{self.shape.to_tksl()}>"


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
    def from_proto(cls, proto_tg: pg.TypeScheme) -> "TypeScheme":
        variables = {
            ts_var.name: Kind.from_proto(ts_var.kind) for ts_var in proto_tg.variables
        }
        constraints = [
            Constraint.from_proto(pg_const) for pg_const in proto_tg.constraints
        ]
        body = cast(GraphType, TierkreisType.from_proto(proto_tg.body))
        return cls(variables, constraints, body)


@dataclass(frozen=True)
class TierkreisTypeError:
    message: str
    location: List[str]

    @classmethod
    def from_proto(cls, proto: ps.TierkreisTypeError) -> "TierkreisTypeError":
        return cls(message=proto.msg, location=proto.location)

    def __str__(self) -> str:
        context = "\n".join(f" - {loc}" for loc in self.location)
        return f"{self.message}\n\nIn context:\n\n{context}"


@dataclass
class TierkreisTypeErrors(Exception):
    errors: List[TierkreisTypeError]

    @classmethod
    def from_proto(cls, proto: ps.TypeErrors) -> "TierkreisTypeErrors":
        return cls(
            errors=[TierkreisTypeError.from_proto(error) for error in proto.errors]
        )

    def __str__(self) -> str:
        separator = "\n\n" + ("─" * 80) + "\n\n"
        return separator.join(str(error) for error in self.errors)

    def __getitem__(self, index: int) -> TierkreisTypeError:
        return self.errors[index]

    def __len__(self) -> int:
        return len(self.errors)
