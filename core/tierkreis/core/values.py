from __future__ import annotations
import typing
from typing import Dict, cast, Any, Callable
import betterproto
import tierkreis.core.protos.tierkreis.graph as pg
from dataclasses import dataclass
from abc import ABC, abstractmethod
from tierkreis.core.internal import python_struct_fields
from pytket.circuit import Circuit  # type: ignore

if typing.TYPE_CHECKING:
    from tierkreis.core.tierkreis_graph import TierkreisGraph

T = typing.TypeVar("T")


class TierkreisValue(ABC):
    @abstractmethod
    def to_proto(self) -> pg.Value:
        pass

    @staticmethod
    def from_proto(value: pg.Value) -> "TierkreisValue":
        """
        Parses a tierkreis type from its protobuf representation.
        """
        name, out_value = betterproto.which_one_of(value, "value")

        if name == "integer":
            return IntValue(out_value or 0)
        elif name == "boolean":
            return BoolValue(out_value or False)
        elif name == "float":
            return FloatValue(out_value or 0.0)
        elif name == "str_":
            return StringValue(out_value or "")
        elif name == "circuit":
            return CircuitValue(out_value)
        elif name == "struct":
            struct_value = cast(pg.StructValue, out_value)
            return StructValue(
                {
                    name: TierkreisValue.from_proto(value)
                    for name, value in struct_value.map.items()
                }
            )
        elif name == "map":
            map_value = cast(pg.MapValue, out_value)
            entries = {}

            for pair_value in map_value.pairs:
                entry_key = TierkreisValue.from_proto(pair_value.first)
                entry_value = TierkreisValue.from_proto(pair_value.second)
                entries[entry_key] = entry_value

            return MapValue(entries)
        elif name == "pair":
            pair_value = cast(pg.PairValue, out_value)
            return PairValue(
                TierkreisValue.from_proto(pair_value.first),
                TierkreisValue.from_proto(pair_value.second),
            )
        elif name == "array":
            array_value = cast(pg.ArrayValue, out_value)
            return ArrayValue(
                [TierkreisValue.from_proto(element) for element in array_value.array]
            )
        else:
            raise ValueError(f"Unknown protobuf value type: {name}")

    @abstractmethod
    def to_python(self, type_: typing.Type[T]) -> T:
        """
        Converts a tierkreis value to a python value given the desired python type.

        When the specified python type is a type variable, the original
        `TierkreisValue` is returned unchanged. This allows us to write generic
        functions in which values of unknown type are passed on as they are.
        """
        pass

    @staticmethod
    def from_python(value: Any) -> "TierkreisValue":
        "Converts a python value to a tierkreis value."

        from tierkreis.core.python import RuntimeGraph, RuntimeStruct

        if isinstance(value, int):
            return IntValue(value)
        elif isinstance(value, str):
            return StringValue(value)
        elif isinstance(value, float):
            return FloatValue(value)
        elif isinstance(value, bool):
            return BoolValue(value)
        elif isinstance(value, tuple):
            return PairValue(
                TierkreisValue.from_python(value[0]),
                TierkreisValue.from_python(value[1]),
            )
        elif isinstance(value, list):
            return ArrayValue(
                [TierkreisValue.from_python(element) for element in value]
            )
        elif isinstance(value, dict):
            return MapValue(
                {
                    element_name: TierkreisValue.from_python(element_value)
                    for element_name, element_value in value.items()
                }
            )
        elif isinstance(value, RuntimeStruct):
            return StructValue(
                {
                    name: TierkreisValue.from_python(value)
                    for name, value in vars(value).items()
                }
            )
        elif isinstance(value, RuntimeGraph):
            return GraphValue(value.graph)
        elif isinstance(value, TierkreisValue):
            return value
        else:
            raise ValueError(
                f"Could not convert python value to tierkreis value: {value}"
            )


@dataclass(frozen=True)
class StringValue(TierkreisValue):
    value: str

    def to_proto(self) -> pg.Value:
        return pg.Value(str_=self.value)

    def to_python(self, type_: typing.Type[T]) -> T:
        if isinstance(type_, typing.TypeVar):
            return cast(T, self)
        if type_ is str:
            return cast(T, self.value)
        else:
            raise TypeError()


@dataclass(frozen=True)
class IntValue(TierkreisValue):
    value: int

    def to_proto(self) -> pg.Value:
        return pg.Value(integer=self.value)

    def to_python(self, type_: typing.Type[T]) -> T:
        if isinstance(type_, typing.TypeVar):
            return cast(T, self)
        if type_ is int:
            return cast(T, self.value)
        else:
            raise TypeError()


@dataclass(frozen=True)
class FloatValue(TierkreisValue):
    value: float

    def to_proto(self) -> pg.Value:
        return pg.Value(flt=self.value)

    def to_python(self, type_: typing.Type[T]) -> T:
        if isinstance(type_, typing.TypeVar):
            return cast(T, self)
        if type_ is float:
            return cast(T, self.value)
        else:
            raise TypeError()


@dataclass(frozen=True)
class BoolValue(TierkreisValue):
    value: bool

    def to_proto(self) -> pg.Value:
        return pg.Value(boolean=self.value)

    def to_python(self, type_: typing.Type[T]) -> T:
        if isinstance(type_, typing.TypeVar):
            return cast(T, self)
        if type_ is bool:
            return cast(T, self.value)
        else:
            raise TypeError()


@dataclass(frozen=True)
class CircuitValue(TierkreisValue):
    value: Circuit

    def to_proto(self) -> pg.Value:
        return pg.Value(circuit=self.value)

    def to_python(self, type_: typing.Type[T]) -> T:
        if isinstance(type_, typing.TypeVar):
            return cast(T, self)
        if type_ is Circuit:
            return cast(T, self.value)
        else:
            raise TypeError()


@dataclass(frozen=True)
class GraphValue(TierkreisValue):
    value: TierkreisGraph

    def to_proto(self) -> pg.Value:
        return pg.Value(graph=self.value.to_proto())

    def to_python(self, type_: typing.Type[T]) -> T:
        from tierkreis.core.python import RuntimeGraph

        if isinstance(type_, typing.TypeVar):
            return cast(T, self)
        if typing.get_origin(type_) is RuntimeGraph:
            return cast(T, self.value)
        else:
            raise TypeError()


@dataclass(frozen=True)
class PairValue(TierkreisValue):
    first: TierkreisValue
    second: TierkreisValue

    def to_proto(self) -> pg.Value:
        return pg.Value(
            pair=pg.PairValue(
                first=self.first.to_proto(),
                second=self.second.to_proto(),
            )
        )

    def to_python(self, type_: typing.Type[T]) -> T:
        if isinstance(type_, typing.TypeVar):
            return cast(T, self)
        elif typing.get_origin(type_) is tuple:
            type_args = typing.get_args(type_)
            first = self.first.to_python(type_args[0])
            second = self.second.to_python(type_args[1])
            return cast(T, (first, second))
        else:
            raise TypeError()


@dataclass(frozen=True)
class ArrayValue(TierkreisValue):
    values: list[TierkreisValue]

    def to_proto(self) -> pg.Value:
        return pg.Value(
            array=pg.ArrayValue(array=[value.to_proto() for value in self.values])
        )

    def to_python(self, type_: typing.Type[T]) -> T:
        if isinstance(type_, typing.TypeVar):
            return cast(T, self)
        elif typing.get_origin(type_) is list:
            type_args = typing.get_args(type_)
            values = [value.to_python(type_args[0]) for value in self.values]
            return cast(T, values)
        else:
            raise TypeError()


@dataclass(frozen=True)
class MapValue(TierkreisValue):
    values: Dict[TierkreisValue, TierkreisValue]

    def to_proto(self) -> pg.Value:
        return pg.Value(
            map=pg.MapValue(
                pairs=[
                    pg.PairValue(first=key.to_proto(), second=value.to_proto())
                    for key, value in self.values.items()
                ]
            )
        )

    def to_python(self, type_: typing.Type[T]) -> T:
        if isinstance(type_, typing.TypeVar):
            return cast(T, self)
        elif typing.get_origin(type_) is dict:
            type_args = typing.get_args(type_)
            values = {
                key.to_python(type_args[0]): value.to_python(type_args[1])
                for key, value in self.values.items()
            }
            return cast(T, values)
        else:
            raise TypeError()


@dataclass(frozen=True)
class StructValue(TierkreisValue):
    values: Dict[str, TierkreisValue]

    def to_proto(self) -> pg.Value:
        return pg.Value(struct=pg.StructValue(map=self.to_proto_dict()))

    def to_python(self, type_: typing.Type[T]) -> T:
        if isinstance(type_, typing.TypeVar):
            return cast(T, self)

        type_origin = typing.get_origin(type_) or type_

        from tierkreis.core.python import RuntimeStruct

        if RuntimeStruct in type_origin.__bases__:
            field_values = {}

            for field_name, field_type in python_struct_fields(type_).items():
                if field_name not in self.values:
                    raise ValueError(f"Missing field {field_name} in struct.")

                field_values[field_name] = self.values[field_name].to_python(field_type)

            return cast(Callable[..., T], type_origin)(**field_values)
        else:
            raise TypeError()

    @staticmethod
    def from_proto_dict(values: dict[str, pg.Value]) -> "StructValue":
        return StructValue(
            {name: TierkreisValue.from_proto(value) for name, value in values.items()}
        )

    def to_proto_dict(self) -> dict[str, pg.Value]:
        return {name: value.to_proto() for name, value in self.values.items()}
