from __future__ import annotations

import typing
from abc import ABC, abstractmethod
from dataclasses import dataclass, is_dataclass
from typing import Any, Callable, ClassVar, Dict, List, Optional, Tuple, TypeVar, cast
from uuid import UUID

import betterproto

import tierkreis.core.protos.tierkreis.graph as pg
from tierkreis.core.internal import python_struct_fields
from tierkreis.core.tierkreis_struct import TierkreisStruct
from tierkreis.core.types import _get_optional_type

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


class NoneConversion(IncompatiblePyType):
    def __str__(self) -> str:
        return (
            super().__str__() + "\nFor None values try using OpionValue(None) directly."
        )


class TierkreisValue(ABC):
    _proto_map: Dict[str, typing.Type["TierkreisValue"]] = dict()
    _pytype_map: Dict[typing.Type, typing.Type["TierkreisValue"]] = dict()

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__()
        TierkreisValue._proto_map[getattr(cls, "_proto_name")] = cls
        TierkreisValue._pytype_map[getattr(cls, "_class_pytype")] = cls

    @property
    def _instance_pytype(self):
        return self._class_pytype

    @abstractmethod
    def to_proto(self) -> pg.Value:
        pass

    @abstractmethod
    def to_tksl(self) -> str:
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
                    tktype
                    for pytype, tktype in cls._pytype_map.items()
                    if pytype is not Optional and isinstance(value, pytype)
                )
            except StopIteration as e:
                if is_dataclass(value):
                    # dataclass that is not an instance of TierkreisStruct
                    # might still be convertible to Struct depending on field types
                    find_subclass = StructValue
                else:
                    exception = (
                        NoneConversion(value)
                        if value is None
                        else IncompatiblePyType(value)
                    )
                    raise exception from e
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
            return self.to_python(self._instance_pytype)
        except ToPythonFailure as _:
            return None


@dataclass(frozen=True)
class OptionValue(TierkreisValue):
    _proto_name: ClassVar[str] = "option"
    _class_pytype: ClassVar[typing.Type] = Optional  # type: ignore
    inner: Optional[TierkreisValue]

    @property
    def _instance_pytype(self):
        return Optional[
            TypeVar("C") if self.inner is None else self.inner._instance_pytype
        ]

    def to_proto(self) -> pg.Value:
        optval = (
            pg.OptionValue(value=self.inner.to_proto())
            if self.inner
            else pg.OptionValue()
        )
        return pg.Value(option=optval)

    def to_python(self, type_: typing.Type[T]) -> T:
        if isinstance(type_, typing.TypeVar):
            return cast(T, self)
        if self.inner is None:
            return cast(T, None)
        if inner_type := _get_optional_type(type_):
            return cast(T, self.inner.to_python(inner_type))
        raise ToPythonFailure(self)

    @classmethod
    def from_python(cls, value: Any) -> "TierkreisValue":
        value = cast(Optional[Any], value)
        optval = None if value is None else TierkreisValue.from_python(value)
        return OptionValue(optval)

    @classmethod
    def from_proto(cls, value: pg.OptionValue) -> "TierkreisValue":
        name, val = betterproto.which_one_of(value, "inner")
        if name == "value":
            return OptionValue(
                TierkreisValue.from_proto(val),
            )
        else:
            return OptionValue(None)

    def __str__(self) -> str:
        return f"Option({str(self.inner)})"

    def to_tksl(self) -> str:
        return f"Some({self.inner.to_tksl()})" if self.inner else "None"


@dataclass(frozen=True)
class BoolValue(TierkreisValue):
    _proto_name: ClassVar[str] = "boolean"
    _class_pytype: ClassVar[typing.Type] = bool

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

    def to_tksl(self) -> str:
        return "true" if self.value else "false"


@dataclass(frozen=True)
class StringValue(TierkreisValue):
    _proto_name: ClassVar[str] = "str"
    _class_pytype: ClassVar[typing.Type] = str
    value: str

    def to_proto(self) -> pg.Value:
        return pg.Value(str=self.value)

    def to_python(self, type_: typing.Type[T]) -> T:
        if isinstance(type_, typing.TypeVar):
            return cast(T, self)
        if type_ is str:
            return cast(T, self.value)
        if type_ is UUID:
            return cast(T, self.value)
        raise ToPythonFailure(self)

    @classmethod
    def from_python(cls, value: Any) -> "TierkreisValue":
        return cls(value or "")

    @classmethod
    def from_proto(cls, value: Any) -> "TierkreisValue":
        return cls(value)

    def __str__(self) -> str:
        return f"String({repr(self.value)})"

    def to_tksl(self) -> str:
        return f'"{self.value}"'


@dataclass(frozen=True)
class IntValue(TierkreisValue):
    _proto_name: ClassVar[str] = "integer"
    _class_pytype: ClassVar[typing.Type] = int
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

    def to_tksl(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class FloatValue(TierkreisValue):
    _proto_name: ClassVar[str] = "flt"
    _class_pytype: ClassVar[typing.Type] = float
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

    def to_tksl(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class PairValue(TierkreisValue):
    _proto_name: ClassVar[str] = "pair"
    _class_pytype: ClassVar[typing.Type] = tuple
    first: TierkreisValue
    second: TierkreisValue

    @property
    def _instance_pytype(self):
        return tuple[self.first._instance_pytype, self.second._instance_pytype]

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

    def to_tksl(self) -> str:
        return f"({self.first.to_tksl()}, {self.second.to_tksl()})"


@dataclass(frozen=True)
class VecValue(TierkreisValue):
    _proto_name: ClassVar[str] = "vec"
    _class_pytype: ClassVar[typing.Type] = list
    values: list[TierkreisValue]

    @property
    def _instance_pytype(self):
        elem_t = (
            TypeVar("E") if len(self.values) == 0 else self.values[0]._instance_pytype
        )
        # Would be better to check all elements are the same.
        return list[elem_t]

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

    def to_tksl(self) -> str:
        return f"[{', '.join(val.to_tksl() for val in self.values)}]"


@dataclass(frozen=True)
class MapValue(TierkreisValue):
    _proto_name: ClassVar[str] = "map"
    _class_pytype: ClassVar[typing.Type] = dict
    values: Dict[TierkreisValue, TierkreisValue]

    @property
    def _instance_pytype(self):
        k = next(iter(self.values.keys()), None)
        key_t = TypeVar("K") if k is None else k._instance_pytype
        v = next(iter(self.values.values()), None)
        val_t = TypeVar("V") if v is None else v._instance_pytype
        # Would be better to check all keys and all values are the same.
        return dict[key_t, val_t]

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

    def to_tksl(self) -> str:
        entries = (
            f"{key.to_tksl()}: {val.to_tksl()}" for key, val in self.values.items()
        )
        return f"{{{', '.join(entries)})}}"


@dataclass(frozen=True)
class StructValue(TierkreisValue):
    _proto_name: ClassVar[str] = "struct"
    _class_pytype: ClassVar[typing.Type] = TierkreisStruct
    values: Dict[str, TierkreisValue]

    def to_proto(self) -> pg.Value:
        return pg.Value(struct=pg.StructValue(map=self.to_proto_dict()))

    def to_python(self, type_: typing.Type[T]) -> T:
        if isinstance(type_, typing.TypeVar):
            return cast(T, self)

        type_origin = typing.get_origin(type_) or type_

        if TierkreisStruct in type_origin.__bases__ or is_dataclass(type_origin):
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
    def from_python(cls, value: TierkreisStruct) -> "StructValue":
        assert is_dataclass(value)
        vals = vars(value)
        types = python_struct_fields(type(value))

        return StructValue(
            {
                name: OptionValue.from_python(value)
                if _get_optional_type(types[name])
                else TierkreisValue.from_python(value)
                for name, value in vals.items()
            }
        )

    @classmethod
    def from_proto(cls, value: Any) -> "StructValue":
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

    def to_tksl(self) -> str:
        key_vals = (f"{key}: {val.to_tksl()}" for key, val in self.values.items())

        return f"Struct{{{', '.join(key_vals)}}}"


@dataclass(frozen=True)
class TierkreisVariant(typing.Generic[T]):
    """Used to represent a Tierkreis Variant as a native python value"""

    tag: str
    value: T


@dataclass(frozen=True)
class VariantValue(TierkreisValue):
    _proto_name: ClassVar[str] = "variant"
    _class_pytype: ClassVar[typing.Type] = TierkreisVariant
    tag: str
    value: TierkreisValue

    @property
    def _instance_pytype(self):
        return TierkreisVariant[self.value._instance_pytype]

    def to_proto(self) -> pg.Value:
        return pg.Value(
            variant=pg.VariantValue(tag=self.tag, value=self.value.to_proto())
        )

    def to_python(self, type_: typing.Type[T]) -> T:
        if isinstance(type_, typing.TypeVar):
            return cast(T, self)
        if typing.get_origin(type_) is TierkreisVariant:
            (type_args,) = typing.get_args(type_)
            return cast(T, TierkreisVariant(self.tag, self.value.to_python(type_args)))
        raise ToPythonFailure(self)

    def to_tksl(self) -> str:
        return f"Variant{{{self.tag}: {self.value.to_tksl()}}}"

    @classmethod
    def from_python(cls, value: TierkreisVariant) -> "TierkreisValue":
        return VariantValue(value.tag, TierkreisValue.from_python(value.value))

    @classmethod
    def from_proto(cls, value: pg.VariantValue) -> "TierkreisValue":
        return VariantValue(value.tag, TierkreisValue.from_proto(value.value))
