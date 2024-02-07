from __future__ import annotations

import typing
from abc import ABC, abstractmethod
from dataclasses import Field, dataclass, fields, make_dataclass
from enum import Enum
from typing import (
    Any,
    Callable,
    ClassVar,
    Dict,
    Generic,
    Iterable,
    Optional,
    Protocol,
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
from tierkreis.core.types import (
    UNIT_TYPE,
    BoolType,
    FloatType,
    GraphType,
    IntType,
    MapType,
    NoneType,
    PairType,
    Row,
    StringType,
    StructType,
    TierkreisPair,
    TierkreisType,
    TupleLabel,
    UnionTag,
    VariantType,
    VarType,
    VecType,
    _extract_literal_type,
    _get_discriminators,
    _get_union_args,
    _is_annotated,
    _is_enum,
)

T = typing.TypeVar("T")
TKVal1 = TypeVar("TKVal1", bound="TierkreisValue")
TKVal2 = TypeVar("TKVal2", bound="TierkreisValue")


@dataclass
class IncompatiblePyType(Exception):
    value: Any

    def __str__(self) -> str:
        return f"Could not convert python value to tierkreis value: {self.value}"


@dataclass
class IncompatibleTierkreisType(Exception):
    value: Any
    tk_type: TierkreisType

    def __str__(self) -> str:
        return (
            f"Could not convert python value: {self.value}, "
            + f"to Tierkreis type: {self.tk_type}"
        )


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
        return getattr(self, "_class_pytype")

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

    def to_python(self, type_: typing.Type[T]) -> T:
        """
        Converts a tierkreis value to a python value given the desired python type.

        When the specified python type is a type variable, the original
        `TierkreisValue` is returned unchanged. This allows us to write generic
        functions in which values of unknown type are passed on as they are.
        """
        if inner_type := _extract_literal_type(type_):
            return self.to_python(inner_type)
        if inner_type := _is_annotated(type_):
            return self.to_python(inner_type)
        if args := _get_union_args(type_):
            # expected type is a union so try converting to each and return the
            # first success.
            for possible in args:
                try:
                    return self.to_python(possible)
                except ToPythonFailure:
                    continue
        raise ToPythonFailure(self)

    @classmethod
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
        if isinstance(value, Enum):
            return VariantValue(value.name, StructValue({}))
        if isinstance(value, tuple):
            # could potentially constrain length here?
            if len(set(type(v) for v in value)) == 1:
                # all of same type - can be Vec
                return VecValue.from_python(value)
            return StructValue.from_tuple(value)
        else:
            find_subclass = next(
                (
                    tktype
                    for pytype, tktype in cls._pytype_map.items()
                    if pytype not in (Optional, None) and isinstance(value, pytype)
                ),
                StructValue,
            )

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
        return super().to_python(type_)

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
        return super().to_python(type_)

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
        return super().to_python(type_)

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
        return super().to_python(type_)

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
    _class_pytype: ClassVar[typing.Type] = TierkreisPair
    first: TKVal1
    second: TKVal2

    @property
    def _instance_pytype(self):
        return TierkreisPair[self.first._instance_pytype, self.second._instance_pytype]

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
        if typing.get_origin(type_) is TierkreisPair:
            type_args = typing.get_args(type_)
            first = self.first.to_python(type_args[0])
            second = self.second.to_python(type_args[1])
            return cast(T, TierkreisPair(first, second))
        return super().to_python(type_)

    @classmethod
    def from_python(cls, value: Any) -> "TierkreisValue":
        value = cast(TierkreisPair[Any, Any], value)
        return PairValue(
            TierkreisValue.from_python(value.first),
            TierkreisValue.from_python(value.second),
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
        if typing.get_origin(type_) in (list, tuple):
            type_args = typing.get_args(type_)
            values = [value.to_python(type_args[0]) for value in self.values]
            return cast(T, values)
        return super().to_python(type_)

    @classmethod
    def from_python(cls, value: Any) -> "TierkreisValue":
        return VecValue(
            [TierkreisValue.from_python(element) for element in cast(Iterable, value)]
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
        return super().to_python(type_)

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


class DataclassInstance(Protocol):
    __dataclass_fields__: ClassVar[dict[str, Field[Any]]]


RowStruct = TypeVar("RowStruct", bound=DataclassInstance)


class StructValue(Generic[RowStruct], TierkreisValue):
    _proto_name: ClassVar[str] = "struct"
    _class_pytype = None
    _struct: RowStruct

    def __init__(self, values: dict[str, TierkreisValue]) -> None:
        __AnonStruct = make_dataclass("__AnonStruct", values.keys())
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

    @property
    def _instance_pytype(self):
        try:
            # if all the keys are tuple labels, report tuple
            arg_vals = _labeled_dict_to_tuple(self.values)
            instance_pytypes = cast(
                tuple[typing.Type, ...], tuple(v._instance_pytype for _, v in arg_vals)
            )
            return tuple[instance_pytypes]  # type: ignore
        except TupleLabel.UnexpectedLabel:
            return super()._instance_pytype

    def to_proto(self) -> pg.Value:
        return pg.Value(struct=pg.StructValue(map=self.to_proto_dict()))

    def to_python(self, type_: typing.Type[T]) -> T:
        if type_ is NoneType:
            return cast(T, None)
        if typing.get_origin(type_) is tuple:
            args = typing.get_args(type_)
            arg_vals = _labeled_dict_to_tuple(self.values)
            converted = [v.to_python(args[i]) for i, v in arg_vals]
            return cast(T, tuple(converted))
        if isinstance(type_, typing.TypeVar):
            return cast(T, self)

        type_origin = typing.get_origin(type_) or type_
        class_fields = python_struct_fields(type_origin)
        field_values = {}
        non_init_values = {}
        for field in class_fields:
            val = self.values[field.name]
            if field.discriminant is not None:
                assert isinstance(val, VariantValue)
                var_types = _get_discriminators(field.type_, field.discriminant)
                assert var_types is not None
                field_type = var_types[val.tag]
                val = val.value
            else:
                field_type = field.type_

            py_val = val.to_python(field_type)
            if field.init:
                # field can be set via __init__ method
                field_values[field.name] = py_val
            else:
                non_init_values[field.name] = py_val
        d_cls = cast(Callable[..., T], type_)(**field_values)
        for k, v in non_init_values.items():
            d_cls.__dict__[k] = v
        return d_cls

    @staticmethod
    def from_proto_dict(values: dict[str, pg.Value]) -> "StructValue":
        return StructValue(
            {name: TierkreisValue.from_proto(value) for name, value in values.items()}
        )

    def to_proto_dict(self) -> dict[str, pg.Value]:
        return {name: value.to_proto() for name, value in self.values.items()}

    @classmethod
    def from_python(cls, value: Any) -> "StructValue":
        class_fields = python_struct_fields(type(value))
        return StructValue(
            {
                field.name: _get_value(
                    getattr(value, field.name),
                    field.type_,
                    field.discriminant,
                )
                for field in class_fields
            }
        )

    @classmethod
    def from_tuple(cls, tup: tuple[Any, ...]) -> "StructValue":
        """Generate a `StructValue` from a tuple using tuple member indices as labels."""
        return StructValue(
            {
                TupleLabel.index_label(i): TierkreisValue.from_python(v)
                for i, v in enumerate(tup)
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


V = TypeVar("V")


def _labeled_dict_to_tuple(labeled_d: dict[str, V]) -> list[tuple[int, V]]:
    # read tuple indices from dictionary keys
    arg_vals = [
        (TupleLabel.parse_label(label), val) for label, val in labeled_d.items()
    ]
    arg_vals.sort(key=lambda x: x[0])
    return arg_vals


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
        if type_ is NoneType and self.tag == UnionTag.none_type_tag():
            return cast(T, None)
        if typing.get_origin(type_) is TierkreisVariant:
            (type_arg,) = typing.get_args(type_)
            return cast(T, TierkreisVariant(self.tag, self.value.to_python(type_arg)))
        if enum_type := _is_enum(type_):
            return getattr(enum_type, self.tag)
        if args := _get_union_args(type_):
            try:
                tag_type_ = UnionTag.parse_type(self.tag, args)
                return self.value.to_python(tag_type_)
            except UnionTag.UnexpectedTag:
                pass
        return cast(T, super().to_python(type_))

    def viz_str(self) -> str:
        return f"Variant{{{self.tag}: {self.value.viz_str()}}}"

    @classmethod
    def from_python(cls, value: TierkreisVariant) -> "TierkreisValue":
        return VariantValue(value.tag, TierkreisValue.from_python(value.value))

    @classmethod
    def from_proto(cls, value: pg.VariantValue) -> "TierkreisValue":
        return VariantValue(value.tag, TierkreisValue.from_proto(value.value))


option_none: VariantValue = VariantValue(UnionTag.none_type_tag(), StructValue({}))


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


def _get_value(value: Any, type_: typing.Type, disc: Optional[str]) -> TierkreisValue:
    if disc:
        tag = getattr(value, disc)
        assert tag is not None
        return VariantValue(tag, TierkreisValue.from_python(value))
    if _get_union_args(type_):
        if value is None:
            return option_none
        return VariantValue(
            UnionTag.value_type_tag(value), TierkreisValue.from_python(value)
        )

    return TierkreisValue.from_python(value)


def val_known_tk_type(tk_type: TierkreisType, value: Any) -> TierkreisValue:
    """Convert a python `value` to a TierkreisValue, given the expected
    `TierkreisType` (`tk_type`)"""
    if isinstance(value, TierkreisValue):
        return value
    err = IncompatibleTierkreisType(value, tk_type)
    rec = val_known_tk_type

    def _check_type(expected: typing.Type | tuple[typing.Type, ...]):
        if not isinstance(value, expected):
            raise err

    if value is None and tk_type == UNIT_TYPE:
        return StructValue({})
    match tk_type:
        case Row(shape) | StructType(shape=Row(shape)):
            return StructValue({k: rec(t, getattr(value, k)) for k, t in shape.items()})
        case IntType():
            _check_type(int)
            return IntValue.from_python(value)
        case BoolType():
            _check_type(bool)
            return BoolValue.from_python(value)
        case FloatType():
            _check_type((float, int))  # promoting int to float is ok
            return FloatValue.from_python(float(value))
        case StringType():
            _check_type(str)
            return StringValue.from_python(value)
        case VarType(_):
            return TierkreisValue.from_python(value)
        case PairType(first, second):
            if hasattr(value, "__len__") and len(value) == 2:
                a, b = value
                return PairValue(rec(first, a), rec(second, b))
            else:
                raise IncompatiblePyType(value)
        case VariantType(Row(shape)):
            union_tag = UnionTag.value_type_tag(value)
            return VariantValue(union_tag, rec(shape[union_tag], value))
        case VecType(element):
            _check_type(typing.Iterable)
            return VecValue([rec(element, v) for v in value])
        case MapType(key, value=value_type):
            _check_type(typing.Mapping)
            return MapValue({rec(key, k): rec(value_type, v) for k, v in value.items()})
        case GraphType(_):
            from tierkreis.core.tierkreis_graph import GraphValue, TierkreisGraph

            assert isinstance(value, TierkreisGraph)
            return GraphValue(value)

    raise err
