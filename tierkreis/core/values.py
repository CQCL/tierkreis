from __future__ import annotations

import typing
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, ClassVar, Dict, List, Optional, Tuple, cast

import betterproto
import tierkreis.core.protos.tierkreis.graph as pg
from tierkreis.core.internal import python_struct_fields
from tierkreis.core.tierkreis_struct import TierkreisStruct
from tierkreis.core.types import NoneType

T = typing.TypeVar("T")


@dataclass
class IncompatiblePyType(Exception):
    value: Any

    def __str__(self) -> str:
        return f"Could not convert python value to tierkreis value: {self.value}"


@dataclass
class ToPythonFailure(Exception):
    value: TierkreisValue

    def __str__(self) -> str:
        return f"Value {self.value} conversion to python type failed."


class TierkreisValue(ABC):
    _proto_map: Dict[str, typing.Type["TierkreisValue"]] = dict()
    _pytype_map: Dict[typing.Type, typing.Type["TierkreisValue"]] = dict()

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__()
        TierkreisValue._proto_map[getattr(cls, "_proto_name")] = cls
        TierkreisValue._pytype_map[getattr(cls, "_pytype")] = cls

    @abstractmethod
    def to_proto(self) -> pg.Value:
        pass

    @classmethod
    def from_proto(cls, value: Any) -> "TierkreisValue":
        """
        Parses a tierkreis type from its protobuf representation.
        """
        name, out_value = betterproto.which_one_of(value, "value")

        try:
            return cls._proto_map[name].from_proto(out_value)
        except KeyError as e:
            raise ValueError(f"Unknown protobuf value type: {name}") from e

    @abstractmethod
    def to_python(self, type_: typing.Type[T]) -> T:
        """
        Converts a tierkreis value to a python value given the desired python type.

        When the specified python type is a type variable, the original
        `TierkreisValue` is returned unchanged. This allows us to write generic
        functions in which values of unknown type are passed on as they are.
        """

    @classmethod
    @abstractmethod
    def from_python(cls, value: Any) -> "TierkreisValue":
        "Converts a python value to a tierkreis value."
        # TODO find workaround for delayed imports
        from tierkreis.core.python import RuntimeGraph
        from tierkreis.core.tierkreis_graph import GraphValue

        if isinstance(value, TierkreisValue):
            return value
        if isinstance(value, RuntimeGraph):
            return GraphValue(value.graph)
        if isinstance(value, bool):
            find_subclass = cls._pytype_map[bool]
        else:
            try:
                find_subclass = next(
                    cls._pytype_map[pytype]
                    for pytype in cls._pytype_map
                    if isinstance(value, pytype)
                )
            except StopIteration as e:
                raise IncompatiblePyType(value) from e
        return find_subclass.from_python(value)

    def try_autopython(self) -> Optional[Any]:
        """Try to automatically convert to a python type without specifying the
        target types.
        Returns None if unsuccesful. Expected to be succesful for "simple" or "leaf"
        types, that are not made up component types.

                :return: Python value if succesful, None if not.
                :rtype: Optional[Any]
        """
        try:
            return self.to_python(getattr(self, "_pytype"))
        except ToPythonFailure as _:
            return None


@dataclass(frozen=True)
class UnitValue(TierkreisValue):
    _proto_name: ClassVar[str] = "unit"
    _pytype: ClassVar[typing.Type] = NoneType  # type: ignore

    def to_proto(self) -> pg.Value:
        return pg.Value(unit=pg.Empty())

    def to_python(self, type_: typing.Type[T]) -> T:
        return cast(T, None)

    @classmethod
    def from_python(cls, value: Any) -> "TierkreisValue":
        return cls()

    @classmethod
    def from_proto(cls, value: Any) -> "TierkreisValue":
        return cls()

    def __str__(self) -> str:
        return f"Unit"


@dataclass(frozen=True)
class BoolValue(TierkreisValue):
    _proto_name: ClassVar[str] = "boolean"
    _pytype: ClassVar[typing.Type] = bool

    value: bool

    def to_proto(self) -> pg.Value:
        return pg.Value(boolean=self.value)

    def to_python(self, type_: typing.Type[T]) -> T:
        if isinstance(type_, typing.TypeVar):
            return cast(T, self)
        if type_ is bool:
            return cast(T, self.value)
        raise ToPythonFailure(self)

    @classmethod
    def from_python(cls, value: Any) -> "TierkreisValue":
        return cls(value or False)

    @classmethod
    def from_proto(cls, value: Any) -> "TierkreisValue":
        return cls(value)

    def __str__(self) -> str:
        return f"Bool({self.value})"


@dataclass(frozen=True)
class StringValue(TierkreisValue):
    _proto_name: ClassVar[str] = "str_"
    _pytype: ClassVar[typing.Type] = str
    value: str

    def to_proto(self) -> pg.Value:
        return pg.Value(str_=self.value)

    def to_python(self, type_: typing.Type[T]) -> T:
        if isinstance(type_, typing.TypeVar):
            return cast(T, self)
        if type_ is str:
            return cast(T, self.value)
        raise ToPythonFailure(self)

    @classmethod
    def from_python(cls, value: Any) -> "TierkreisValue":
        return cls(value or "")

    @classmethod
    def from_proto(cls, value: Any) -> "TierkreisValue":
        return cls(value)

    def __str__(self) -> str:
        return f'String("{self.value}")'


@dataclass(frozen=True)
class IntValue(TierkreisValue):
    _proto_name: ClassVar[str] = "integer"
    _pytype: ClassVar[typing.Type] = int
    value: int

    def to_proto(self) -> pg.Value:
        return pg.Value(integer=self.value)

    def to_python(self, type_: typing.Type[T]) -> T:
        if isinstance(type_, typing.TypeVar):
            return cast(T, self)
        if type_ is int:
            return cast(T, self.value)
        else:
            raise ToPythonFailure(self)

    @classmethod
    def from_python(cls, value: Any) -> "TierkreisValue":
        return cls(value or 0)

    @classmethod
    def from_proto(cls, value: Any) -> "TierkreisValue":
        return cls(value)

    def __str__(self) -> str:
        return f"Int({self.value})"


@dataclass(frozen=True)
class FloatValue(TierkreisValue):
    _proto_name: ClassVar[str] = "flt"
    _pytype: ClassVar[typing.Type] = float
    value: float

    def to_proto(self) -> pg.Value:
        return pg.Value(flt=self.value)

    def to_python(self, type_: typing.Type[T]) -> T:
        if isinstance(type_, typing.TypeVar):
            return cast(T, self)
        if type_ is float:
            return cast(T, self.value)
        else:
            raise ToPythonFailure(self)

    @classmethod
    def from_python(cls, value: Any) -> "TierkreisValue":
        return cls(value or 0.0)

    @classmethod
    def from_proto(cls, value: Any) -> "TierkreisValue":
        return cls(value)

    def __str__(self) -> str:
        return f"Float({self.value})"


@dataclass(frozen=True)
class PairValue(TierkreisValue):
    _proto_name: ClassVar[str] = "pair"
    _pytype: ClassVar[typing.Type] = tuple
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
        if typing.get_origin(type_) is tuple:
            type_args = typing.get_args(type_)
            first = self.first.to_python(type_args[0])
            second = self.second.to_python(type_args[1])
            return cast(T, (first, second))
        raise ToPythonFailure(self)

    @classmethod
    def from_python(cls, value: Any) -> "TierkreisValue":
        value = cast(Tuple[Any, Any], value)
        return PairValue(
            TierkreisValue.from_python(value[0]),
            TierkreisValue.from_python(value[1]),
        )

    @classmethod
    def from_proto(cls, value: Any) -> "TierkreisValue":
        pair_value = cast(pg.PairValue, value)
        return PairValue(
            TierkreisValue.from_proto(pair_value.first),
            TierkreisValue.from_proto(pair_value.second),
        )

    def __str__(self) -> str:
        return f"Pair({str(self.first)}, {str(self.second)})"


@dataclass(frozen=True)
class VecValue(TierkreisValue):
    _proto_name: ClassVar[str] = "vec"
    _pytype: ClassVar[typing.Type] = list
    values: list[TierkreisValue]

    def to_proto(self) -> pg.Value:
        return pg.Value(
            vec=pg.VecValue(vec=[value.to_proto() for value in self.values])
        )

    def to_python(self, type_: typing.Type[T]) -> T:
        if isinstance(type_, typing.TypeVar):
            return cast(T, self)
        if typing.get_origin(type_) is list:
            type_args = typing.get_args(type_)
            values = [value.to_python(type_args[0]) for value in self.values]
            return cast(T, values)
        raise ToPythonFailure(self)

    @classmethod
    def from_python(cls, value: Any) -> "TierkreisValue":
        return VecValue(
            [TierkreisValue.from_python(element) for element in cast(List, value)]
        )

    @classmethod
    def from_proto(cls, value: Any) -> "TierkreisValue":
        vec_value = cast(pg.VecValue, value)
        return VecValue(
            [TierkreisValue.from_proto(element) for element in vec_value.vec]
        )

    def __str__(self) -> str:
        return f"Vec({','.join(map(str, self.values))})"


@dataclass(frozen=True)
class MapValue(TierkreisValue):
    _proto_name: ClassVar[str] = "map"
    _pytype: ClassVar[typing.Type] = dict
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
        if typing.get_origin(type_) is dict:
            type_args = typing.get_args(type_)
            values = {
                key.to_python(type_args[0]): value.to_python(type_args[1])
                for key, value in self.values.items()
            }
            return cast(T, values)
        raise ToPythonFailure(self)

    @classmethod
    def from_python(cls, value: Any) -> "TierkreisValue":
        return MapValue(
            {
                TierkreisValue.from_python(element_key): TierkreisValue.from_python(
                    element_value
                )
                for element_key, element_value in value.items()
            }
        )

    @classmethod
    def from_proto(cls, value: Any) -> "TierkreisValue":
        map_value = cast(pg.MapValue, value)
        entries = {}

        for pair_value in map_value.pairs:
            entry_key = TierkreisValue.from_proto(pair_value.first)
            entry_value = TierkreisValue.from_proto(pair_value.second)
            entries[entry_key] = entry_value

        return MapValue(entries)

    def __str__(self) -> str:
        return f"Map({', '.join(f'{key}: {val}' for key, val in self.values.items())})"


@dataclass(frozen=True)
class StructValue(TierkreisValue):
    _proto_name: ClassVar[str] = "struct"
    _pytype: ClassVar[typing.Type] = TierkreisStruct
    values: Dict[str, TierkreisValue]

    def to_proto(self) -> pg.Value:
        return pg.Value(struct=pg.StructValue(map=self.to_proto_dict()))

    def to_python(self, type_: typing.Type[T]) -> T:
        if isinstance(type_, typing.TypeVar):
            return cast(T, self)

        type_origin = typing.get_origin(type_) or type_

        if TierkreisStruct in type_origin.__bases__:
            field_values = {}

            for field_name, field_type in python_struct_fields(type_).items():
                if field_name not in self.values:
                    raise ValueError(f"Missing field {field_name} in struct.")

                field_values[field_name] = self.values[field_name].to_python(field_type)

            return cast(Callable[..., T], type_origin)(**field_values)

        raise ToPythonFailure(self)

    @staticmethod
    def from_proto_dict(values: dict[str, pg.Value]) -> "StructValue":
        return StructValue(
            {name: TierkreisValue.from_proto(value) for name, value in values.items()}
        )

    def to_proto_dict(self) -> dict[str, pg.Value]:
        return {name: value.to_proto() for name, value in self.values.items()}

    @classmethod
    def from_python(cls, value: Any) -> "TierkreisValue":
        return StructValue(
            {
                name: TierkreisValue.from_python(value)
                for name, value in vars(cast(TierkreisStruct, value)).items()
            }
        )

    @classmethod
    def from_proto(cls, value: Any) -> "TierkreisValue":
        struct_value = cast(pg.StructValue, value)
        return StructValue(
            {
                name: TierkreisValue.from_proto(value)
                for name, value in struct_value.map.items()
            }
        )

    def __str__(self) -> str:
        key_vals = (f"{key}: {str(val)}" for key, val in self.values.items())
        return f"Struct{{{', '.join(key_vals)}}}"
