from __future__ import annotations

import typing
from abc import ABC, abstractmethod
from dataclasses import dataclass, fields, is_dataclass, make_dataclass
from typing import (
    Any,
    Callable,
    ClassVar,
    Dict,
    Generic,
    List,
    Optional,
    Tuple,
    TypeVar,
    cast,
    get_args,
    get_origin,
    get_type_hints,
)
from uuid import UUID

import betterproto

import tierkreis.core.protos.tierkreis.v1alpha.graph as pg
from tierkreis.core import types as TKType
from tierkreis.core.internal import python_struct_fields
from tierkreis.core.tierkreis_struct import TierkreisStruct
from tierkreis.core.types import NoneType, TierkreisType, _get_optional_type

from . import Labels

T = typing.TypeVar("T")
TKVal1 = TypeVar("TKVal1", bound="TierkreisValue")
TKVal2 = TypeVar("TKVal2", bound="TierkreisValue")


@dataclass
class IncompatiblePyType(Exception):
    value: Any

    def __str__(self) -> str:
        msg = f"Could not convert python value to tierkreis value: {self.value}"
        value_type = type(self.value)
        if is_dataclass(value_type) and not issubclass(value_type, TierkreisStruct):
            msg += (
                f". Try calling {register_struct_convertible.__name__}"
                f" with its type ({value_type})."
            )
        return msg


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
        TierkreisValue._pytype_map[getattr(cls, "_class_pytype")] = cls

    @property
    def _instance_pytype(self):
        return self._class_pytype

    @abstractmethod
    def to_proto(self) -> pg.Value:
        pass

    @abstractmethod
    def viz_str(self) -> str:
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
        if value is None:
            return option_none
        else:
            try:
                find_subclass = next(
                    tktype
                    for pytype, tktype in cls._pytype_map.items()
                    if pytype is not Optional and isinstance(value, pytype)
                )
            except StopIteration as e:
                raise IncompatiblePyType(value) from e
        return find_subclass.from_python(value)

    @classmethod
    def from_python_optional(cls, val: Optional[Any]) -> "TierkreisValue":
        if val is None:
            return option_none
        return option_some(cls.from_python(val))

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


def register_struct_convertible(struct_class: typing.Type):
    """Instructs subsequent calls of TierkreisValue.from_python to convert
    instances of the supplied class (which must be a dataclass) into StructValues.
    Otherwise, such conversion is only applied to subclasses of TierkreisStruct."""
    if not is_dataclass(struct_class):
        raise ValueError("Can only convert dataclasses")
    TierkreisValue._pytype_map[struct_class] = StructValue


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

    def viz_str(self) -> str:
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

    def viz_str(self) -> str:
        return f'"{self.value}"'


@dataclass(frozen=True)
class IntValue(TierkreisValue):
    _proto_name: ClassVar[str] = "integer"
    _class_pytype: ClassVar[typing.Type] = int
    value: int

    assert isinstance(True, int)  # Yes python!! So, check dict iteration order
    assert bool in TierkreisValue._pytype_map  # will find entry for bool first.

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

    def viz_str(self) -> str:
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

    def viz_str(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class PairValue(Generic[TKVal1, TKVal2], TierkreisValue):
    _proto_name: ClassVar[str] = "pair"
    _class_pytype: ClassVar[typing.Type] = tuple
    first: TKVal1
    second: TKVal2

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

    def viz_str(self) -> str:
        return f"({self.first.viz_str()}, {self.second.viz_str()})"


@dataclass(frozen=True)
class VecValue(Generic[TKVal1], TierkreisValue):
    _proto_name: ClassVar[str] = "vec"
    _class_pytype: ClassVar[typing.Type] = list
    values: list[TKVal1]

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

    def viz_str(self) -> str:
        return f"[{', '.join(val.viz_str() for val in self.values)}]"


@dataclass(frozen=True)
class MapValue(Generic[TKVal1, TKVal2], TierkreisValue):
    _proto_name: ClassVar[str] = "map"
    _class_pytype: ClassVar[typing.Type] = dict
    values: Dict[TKVal1, TKVal2]

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

    def viz_str(self) -> str:
        entries = (
            f"{key.viz_str()}: {val.viz_str()}" for key, val in self.values.items()
        )
        return f"{{{', '.join(entries)})}}"


RowStruct = TypeVar("RowStruct", bound=TierkreisStruct)


class StructValue(Generic[RowStruct], TierkreisValue):
    _proto_name: ClassVar[str] = "struct"
    _class_pytype: ClassVar[typing.Type] = TierkreisStruct
    _struct: RowStruct

    def __init__(self, values: dict[str, TierkreisValue]) -> None:
        __AnonStruct = make_dataclass(
            "__AnonStruct", values.keys(), bases=(TierkreisStruct,)
        )
        self._struct = __AnonStruct(**values)

    def __eq__(self, __o: object) -> bool:
        if not isinstance(__o, StructValue):
            return False
        return self.values == __o.values

    @property
    def values(self) -> dict[str, TierkreisValue]:
        return {
            k: getattr(self._struct, k) for k in (f.name for f in fields(self._struct))
        }

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
                name: TierkreisValue.from_python_optional(value)
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

    def viz_str(self) -> str:
        key_vals = (f"{key}: {val.viz_str()}" for key, val in self.values.items())

        return f"Struct{{{', '.join(key_vals)}}}"


@dataclass(frozen=True)
class TierkreisVariant(typing.Generic[T]):
    """Used to represent a Tierkreis Variant as a native python value"""

    tag: str
    value: T


@dataclass(frozen=True)
class VariantValue(Generic[RowStruct], TierkreisValue):
    _proto_name: ClassVar[str] = "variant"
    _class_pytype: ClassVar[typing.Type] = TierkreisVariant
    tag: str
    value: TierkreisValue

    @property
    def _instance_pytype(self):
        if self.tag == Labels.SOME:
            return Optional[self.value._instance_pytype]
        if self == option_none:
            return Optional[Any]
        return TierkreisVariant[self.value._instance_pytype]

    def to_proto(self) -> pg.Value:
        return pg.Value(
            variant=pg.VariantValue(tag=self.tag, value=self.value.to_proto())
        )

    def to_python(self, type_: typing.Type[T]) -> T:
        if isinstance(type_, typing.TypeVar):
            return cast(T, self)
        if typing.get_origin(type_) is TierkreisVariant:
            (type_arg,) = typing.get_args(type_)
            return cast(T, TierkreisVariant(self.tag, self.value.to_python(type_arg)))
        elif self == option_none:
            assert type_ is NoneType or _get_optional_type(type_) is not None
            return cast(T, None)
        elif (inner_t := _get_optional_type(type_)) and self.tag == Labels.SOME:
            return cast(T, self.value.to_python(inner_t))
        raise ToPythonFailure(self)

    def viz_str(self) -> str:
        return f"Variant{{{self.tag}: {self.value.viz_str()}}}"

    @classmethod
    def from_python(cls, value: TierkreisVariant) -> "TierkreisValue":
        return VariantValue(value.tag, TierkreisValue.from_python(value.value))

    @classmethod
    def from_proto(cls, value: pg.VariantValue) -> "TierkreisValue":
        return VariantValue(value.tag, TierkreisValue.from_proto(value.value))


option_none: VariantValue = VariantValue(Labels.NONE, StructValue({}))


def option_some(inner: TierkreisValue) -> VariantValue:
    return VariantValue(Labels.SOME, inner)


def _typeddict_to_row(typeddict: dict[str, TierkreisValue]) -> TKType.Row:
    return TKType.Row(
        {key: tkvalue_to_tktype(val) for key, val in get_type_hints(typeddict).items()}
    )


def tkvalue_to_tktype(val_cls: typing.Type[TierkreisValue]) -> TierkreisType:
    if get_origin(val_cls) == VecValue:
        (inner,) = get_args(val_cls)
        return TKType.VecType(tkvalue_to_tktype(inner))
    if get_origin(val_cls) == VariantValue:
        (typeddict,) = get_args(val_cls)
        return TKType.VariantType(_typeddict_to_row(typeddict))

    if get_origin(val_cls) == StructValue:
        (typeddict,) = get_args(val_cls)
        return TKType.StructType(_typeddict_to_row(typeddict))
    if get_origin(val_cls) == PairValue:
        first, second = get_args(val_cls)
        return TKType.PairType(*map(tkvalue_to_tktype, (first, second)))
    if get_origin(val_cls) == MapValue:
        first, second = get_args(val_cls)
        return TKType.MapType(*map(tkvalue_to_tktype, (first, second)))

    if val_cls == IntValue:
        return TKType.IntType()

    if val_cls == BoolValue:
        return TKType.BoolType()

    if val_cls == FloatValue:
        return TKType.FloatType()

    if val_cls == StringValue:
        return TKType.StringType()

    raise ValueError("Cannot convert value class.")
