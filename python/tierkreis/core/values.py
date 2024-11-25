"""Tierkreis values and utilities for converting between Python and Tierkreis values."""

from __future__ import annotations

import inspect
import json
import typing
import warnings
from abc import ABC, abstractmethod
from dataclasses import Field, dataclass, fields, make_dataclass
from enum import Enum
from types import UnionType
from typing import (
    Any,
    Callable,
    ClassVar,
    Dict,
    Generic,
    Iterable,
    Mapping,
    Optional,
    Protocol,
    TypeVar,
    cast,
)
from uuid import UUID

import betterproto

import tierkreis.core.protos.tierkreis.v1alpha1.graph as pg
from tierkreis.core._internal import (
    ClassField,
    FieldExtractionError,
    generic_origin,
    python_struct_fields,
)
from tierkreis.core.opaque_model import (
    OpaqueModel,
)
from tierkreis.core.types import (
    NoneType,
    TierkreisPair,
    TierkreisType,
    TupleLabel,
    UnionTag,
    _extract_literal_type,
    _get_discriminators,
    _get_union_args,
    _is_annotated,
    _is_enum,
    _is_var_length_tuple,
)

T = typing.TypeVar("T")
TKVal1 = TypeVar("TKVal1", bound="TierkreisValue")
TKVal2 = TypeVar("TKVal2", bound="TierkreisValue")


@dataclass
class IncompatiblePyValue(Exception):
    """Python value could not be converted to a Tierkreis value."""

    value: Any

    def __str__(self) -> str:
        return (
            f"Could not convert python value to tierkreis value: {self.value}."
            + "Try providing a type annotation to `TierkreisValue.from_python`."
        )


@dataclass
class IncompatibleAnnotatedValue(IncompatiblePyValue):
    """Could not convert value to type declared by annotation."""

    type_: typing.Type

    def __str__(self) -> str:
        return (
            f"Could not convert python value: {self.value}, "
            + f"with type annotation: {self.type_}"
        )


@dataclass
class ToPythonFailure(Exception):
    """Could not convert a Tierkreis value to a python value."""

    value: TierkreisValue

    def __str__(self) -> str:
        return f"Value {self.value} conversion to python type failed."


class TierkreisValue(ABC):
    """Abstract base class for all Tierkreis compatible values."""

    _proto_map: Dict[str, typing.Type["TierkreisValue"]] = dict()

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__()
        TierkreisValue._proto_map[getattr(cls, "_proto_name")] = cls

    @property
    def _instance_pytype(self) -> typing.Type:
        raise NotImplementedError

    @abstractmethod
    def to_proto(self) -> pg.Value:
        pass

    @abstractmethod
    def viz_str(self) -> str:
        """String representation used in graph visualisation."""
        pass

    @classmethod
    def from_proto(cls, value: Any) -> "TierkreisValue":
        """Parses a tierkreis type from its protobuf representation."""
        name, out_value = betterproto.which_one_of(value, "value")

        try:
            return cls._proto_map[name].from_proto(out_value)
        except KeyError as e:
            raise ValueError(f"Unknown protobuf value type: {name}") from e

    @abstractmethod
    def _to_python_impl(self, type_: typing.Type[T]) -> T | None:
        """Each subclass should implement this method to convert to associated
        python type if possible.
        """
        ...

    def to_python(self, type_: typing.Type[T]) -> T:
        """Converts a tierkreis value to a python value given the desired python type.

        When the specified python type is a type variable, the original
        `TierkreisValue` is returned unchanged. This allows us to write generic
        functions in which values of unknown type are passed on as they are.
        """
        if isinstance(type_, typing.TypeVar):
            return cast(T, self)

        if alternative := TierkreisType._convert_as.get(type_):
            alt_value = self.to_python(alternative)
            return alt_value.from_tierkreis_compatible()
        if type_ is NoneType:
            return cast(T, None)
        if (py_val := self._to_python_impl(type_)) is not None:
            # check if known type to subclass
            return py_val
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

    def to_python_union(self, type_: UnionType) -> Any:
        """Converts a tierkreis value to a python value given the desired union type."""
        return self.to_python(type_)  # type: ignore

    @classmethod
    def from_python(
        cls, value: Any, type_: typing.Type | None = None
    ) -> "TierkreisValue":
        """Converts a python value to a tierkreis value. If `type_` is not provided, it is inferred from the value."""
        try:
            some_type = type_ or type(value)
            # TODO find workaround for delayed imports
            from tierkreis.core.python import RuntimeGraph
            from tierkreis.core.tierkreis_graph import GraphValue

            if alternative := TierkreisType._convert_as.get(some_type):
                return TierkreisValue.from_python(
                    alternative.new_tierkreis_compatible(value), alternative
                )
            if isinstance(value, OpaqueModel):
                return _opaque_to_struct(value)
            if isinstance(value, TierkreisValue):
                return value
            if isinstance(value, RuntimeGraph):
                return GraphValue(value.graph)
            if value is None:
                return option_none
            if isinstance(value, Enum):
                return VariantValue(value.name, StructValue({}))

            return _val_known_type(some_type, value)
        except IncompatiblePyValue as e:
            if type_ is not None:
                raise IncompatibleAnnotatedValue(value, type_) from e
            raise e

    @classmethod
    def from_python_union(cls, value: Any, type_: UnionType) -> "TierkreisValue":
        """Converts a python value to a tierkreis value, given a target python Union type."""

        return cls.from_python(value, type_)  # type: ignore

    def try_autopython(self) -> Optional[Any]:
        """Try to automatically convert to a python type without specifying the
        target types.
        Returns None if unsuccessful. Expected to be successful for "simple" or "leaf"
        types, that are not made up component types.

                :return: Python value if successful, None if not.
                :rtype: Optional[Any]
        """
        try:
            return self.to_python(self._instance_pytype)
        except (ToPythonFailure, NotImplementedError) as _:
            return None


@dataclass(frozen=True)
class BoolValue(TierkreisValue):
    """Boolean."""

    _proto_name: ClassVar[str] = "boolean"

    value: bool

    @property
    def _instance_pytype(self) -> typing.Type:
        return bool

    def to_proto(self) -> pg.Value:
        return pg.Value(boolean=self.value)

    def _to_python_impl(self, type_: typing.Type[T]) -> T | None:
        if type_ is bool:
            return cast(T, self.value)

    @classmethod
    def from_proto(cls, value: Any) -> "TierkreisValue":
        return cls(value)

    def __str__(self) -> str:
        return f"Bool({self.value})"

    def viz_str(self) -> str:
        return "true" if self.value else "false"


@dataclass(frozen=True)
class StringValue(TierkreisValue):
    """UTF-8 encoded string."""

    _proto_name: ClassVar[str] = "str"
    value: str

    @property
    def _instance_pytype(self) -> typing.Type:
        return str

    def to_proto(self) -> pg.Value:
        return pg.Value(str=self.value)

    def _to_python_impl(self, type_: typing.Type[T]) -> T | None:
        if type_ is str:
            return cast(T, self.value)
        if type_ is UUID:
            return cast(T, self.value)

    @classmethod
    def from_proto(cls, value: Any) -> "TierkreisValue":
        return cls(value)

    def __str__(self) -> str:
        return f"String({repr(self.value)})"

    def viz_str(self) -> str:
        return f'"{self.value}"'


@dataclass(frozen=True)
class IntValue(TierkreisValue):
    """Signed integer."""

    _proto_name: ClassVar[str] = "integer"
    value: int

    @property
    def _instance_pytype(self) -> typing.Type:
        return int

    def to_proto(self) -> pg.Value:
        return pg.Value(integer=self.value)

    def _to_python_impl(self, type_: typing.Type[T]) -> T | None:
        if type_ is int:
            return cast(T, self.value)

    @classmethod
    def from_proto(cls, value: Any) -> "TierkreisValue":
        return cls(value)

    def __str__(self) -> str:
        return f"Int({self.value})"

    def viz_str(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class FloatValue(TierkreisValue):
    """IEEE 754 double precision floating point number."""

    _proto_name: ClassVar[str] = "flt"
    value: float

    @property
    def _instance_pytype(self) -> typing.Type:
        return float

    def to_proto(self) -> pg.Value:
        return pg.Value(flt=self.value)

    def _to_python_impl(self, type_: typing.Type[T]) -> T | None:
        if type_ is float:
            return cast(T, self.value)

    @classmethod
    def from_proto(cls, value: Any) -> "TierkreisValue":
        return cls(value)

    def __str__(self) -> str:
        return f"Float({self.value})"

    def viz_str(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class PairValue(Generic[TKVal1, TKVal2], TierkreisValue):
    """A pair of two types."""

    _proto_name: ClassVar[str] = "pair"
    first: TKVal1
    second: TKVal2

    @property
    def _instance_pytype(self) -> typing.Type:
        return TierkreisPair[self.first._instance_pytype, self.second._instance_pytype]

    def to_proto(self) -> pg.Value:
        return pg.Value(
            pair=pg.PairValue(
                first=self.first.to_proto(),
                second=self.second.to_proto(),
            )
        )

    def _to_python_impl(self, type_: typing.Type[T]) -> T | None:
        if typing.get_origin(type_) is TierkreisPair:
            type_args = typing.get_args(type_)
            first = self.first.to_python(type_args[0])
            second = self.second.to_python(type_args[1])
            return cast(T, TierkreisPair(first, second))

    @classmethod
    def from_tierkreis_pair(cls, value: TierkreisPair) -> "TierkreisValue":
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
    """A vector of elements of the same type."""

    _proto_name: ClassVar[str] = "vec"
    values: list[TKVal1]

    @property
    def _instance_pytype(self) -> typing.Type:
        elem_t = (
            TypeVar("E") if len(self.values) == 0 else self.values[0]._instance_pytype
        )
        # Would be better to check all elements are the same.
        return list[elem_t]

    def to_proto(self) -> pg.Value:
        return pg.Value(
            vec=pg.VecValue(vec=[value.to_proto() for value in self.values])
        )

    def _to_python_impl(self, type_: typing.Type[T]) -> T | None:
        if typing.get_origin(type_) in (list, tuple):
            type_args = typing.get_args(type_)
            values = [value.to_python(type_args[0]) for value in self.values]
            return cast(T, values)

    @classmethod
    def from_iterable(cls, value: Iterable) -> "TierkreisValue":
        return VecValue([TierkreisValue.from_python(element) for element in value])

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
    """A map from keys of one type to values of another. The key type must be hashable."""

    _proto_name: ClassVar[str] = "map"
    values: Dict[TKVal1, TKVal2]

    @property
    def _instance_pytype(self) -> typing.Type:
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

    def _to_python_impl(self, type_: typing.Type[T]) -> T | None:
        if typing.get_origin(type_) is dict:
            type_args = typing.get_args(type_)
            values = {
                key.to_python(type_args[0]): value.to_python(type_args[1])
                for key, value in self.values.items()
            }
            return cast(T, values)

    @classmethod
    def from_mapping(cls, value: Mapping) -> "TierkreisValue":
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


def _opaque_to_struct(opaque: OpaqueModel) -> StructValue:
    return StructValue(
        {opaque.tierkreis_field(): StringValue(opaque.model_dump_json())}
    )


class DataclassInstance(Protocol):
    __dataclass_fields__: ClassVar[dict[str, Field[Any]]]


RowStruct = TypeVar("RowStruct", bound=DataclassInstance)


class StructValue(Generic[RowStruct], TierkreisValue):
    """A composite structure of named fields."""

    _proto_name: ClassVar[str] = "struct"
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
    def _instance_pytype(self) -> typing.Type:
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

    def _to_python_impl(self, type_: typing.Type[T]) -> T | None:
        type_origin = typing.get_origin(type_) or type_

        if type_origin is tuple:
            args = typing.get_args(type_)
            arg_vals = _labeled_dict_to_tuple(self.values)
            converted = [v.to_python(args[i]) for i, v in arg_vals]
            return cast(T, tuple(converted))
        vals = self.values
        if inspect.isclass(type_) and issubclass(type_, OpaqueModel):
            ((fieldname, payload),) = vals.items()  # Exactly one entry
            assert fieldname == type_.tierkreis_field()
            assert isinstance(payload, StringValue)
            py_val = json.loads(payload.value)
            return cast(Callable[..., T], type_)(**py_val)
        try:
            class_fields = python_struct_fields(type_)
        except FieldExtractionError as e:
            raise ToPythonFailure(self) from e

        field_values = {}
        non_init_values = {}
        for field in class_fields:
            val = vals[field.name]
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
    def from_object(cls, value: Any, type_: typing.Type | None = None) -> "StructValue":
        """Generate a `StructValue` from a python object using object member names as labels."""
        struct_type = type_ or type(value)
        try:
            class_fields = python_struct_fields(struct_type)
        except FieldExtractionError as e:
            raise IncompatiblePyValue(value) from e

        def _extract_value(field: ClassField) -> TierkreisValue:
            field_value = getattr(value, field.name)
            if field_value is None:
                return option_none

            union_args = _get_union_args(field.type_)
            if field.discriminant:
                # try to figure out which variant the field_value is
                tag = getattr(field_value, field.discriminant)
                assert tag is not None
                variant_type = None
                if union_args:

                    def _discriminant_matches(fields: list[ClassField]) -> bool:
                        # check if any field has the discriminant field, the
                        # default of which matches the tag
                        return any(
                            f.name == field.discriminant and f.default == tag
                            for f in fields
                        )

                    # attempt to find the type annotation matching the tag
                    variant_type = next(
                        (
                            a
                            for a in union_args
                            if _discriminant_matches(python_struct_fields(a))
                        ),
                        None,
                    )
                return VariantValue(
                    tag, TierkreisValue.from_python(field_value, variant_type)
                )
            if union_args:
                value_tag = UnionTag.value_type_tag(field_value)
                variant_type = next(
                    (a for a in union_args if UnionTag.type_tag(a) == value_tag), None
                )
                return VariantValue(
                    UnionTag.value_type_tag(field_value),
                    TierkreisValue.from_python(field_value, variant_type),
                )

            return TierkreisValue.from_python(field_value, field.type_)

        return cls({field.name: _extract_value(field) for field in class_fields})

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
    """Used to represent a Tierkreis Variant as a native python value. Defined
    by string tag and value.
    """

    tag: str
    value: T


@dataclass(frozen=True)
class VariantValue(Generic[RowStruct], TierkreisValue):
    _proto_name: ClassVar[str] = "variant"
    tag: str
    value: TierkreisValue

    @property
    def _instance_pytype(self) -> typing.Type:
        if self == option_none:
            return Optional[Any]  # type: ignore[reportReturnType]
        return TierkreisVariant[self.value._instance_pytype]

    def to_proto(self) -> pg.Value:
        return pg.Value(
            variant=pg.VariantValue(tag=self.tag, value=self.value.to_proto())
        )

    def _to_python_impl(self, type_: typing.Type[T]) -> T | None:
        if type_ is NoneType and self.tag == UnionTag.none_type_tag():
            return cast(T, None)
        if typing.get_origin(type_) is TierkreisVariant:
            (type_arg,) = typing.get_args(type_)
            return cast(T, TierkreisVariant(self.tag, self.value.to_python(type_arg)))
        if enum_type := _is_enum(type_):
            if not hasattr(enum_type, self.tag):
                raise ToPythonFailure(self)
            return getattr(enum_type, self.tag)
        if args := _get_union_args(type_):
            try:
                tag_type_ = UnionTag.parse_type(self.tag, args)
                return self.value.to_python(tag_type_)
            except UnionTag.UnexpectedTag:
                pass

    def viz_str(self) -> str:
        return f"Variant{{{self.tag}: {self.value.viz_str()}}}"

    @classmethod
    def from_tierkreis_variant(
        cls, value: TierkreisVariant, inner_type: typing.Type | None
    ) -> "TierkreisValue":
        return VariantValue(
            value.tag, TierkreisValue.from_python(value.value, inner_type)
        )

    @classmethod
    def from_proto(cls, value: pg.VariantValue) -> "TierkreisValue":
        return VariantValue(value.tag, TierkreisValue.from_proto(value.value))


option_none: VariantValue = VariantValue(UnionTag.none_type_tag(), StructValue({}))


def _val_known_type(type_: typing.Type, value: Any) -> TierkreisValue:
    """Convert a python `value` to a TierkreisValue, given a python type annotation."""
    if type_ is int:
        return IntValue(value)
    if type_ is bool:
        return BoolValue(value)
    if type_ is float:
        if isinstance(value, int):
            # int -> float is an acceptable coercion
            return FloatValue(float(value))
        return FloatValue(value)
    if type_ is str:
        return StringValue(value)

    from tierkreis.core.tierkreis_graph import GraphValue, TierkreisGraph

    if type_ is TierkreisGraph:
        assert isinstance(value, TierkreisGraph)
        return GraphValue(value)

    # types that may contain other types

    type_origin = typing.get_origin(type_) or type_
    type_args = typing.get_args(type_)

    if type_origin is TierkreisVariant:
        try:
            (inner_type,) = type_args
        except ValueError:
            inner_type = None
        return VariantValue.from_tierkreis_variant(value, inner_type)

    if type_origin is tuple:
        if elem_type := _is_var_length_tuple(type_args):
            return VecValue.from_iterable(
                TierkreisValue.from_python(v, elem_type) for v in value
            )
        if type_args:
            return StructValue.from_tuple(
                tuple(
                    TierkreisValue.from_python(v, elem_t)
                    for elem_t, v in zip(type_args, value)
                )
            )
        return StructValue.from_tuple(value)

    if type_origin is list:
        if type_args:
            return VecValue.from_iterable(
                TierkreisValue.from_python(v, type_args[0]) for v in value
            )
        return VecValue.from_iterable(value)
    if type_origin is dict:
        if type_args:
            return MapValue.from_mapping(
                {
                    TierkreisValue.from_python(
                        k, type_args[0]
                    ): TierkreisValue.from_python(v, type_args[1])
                    for k, v in value.items()
                }
            )
        return MapValue.from_mapping(value)
    if type_origin is TierkreisPair:
        if type_args:
            return PairValue(
                TierkreisValue.from_python(value.first, type_args[0]),
                TierkreisValue.from_python(value.second, type_args[1]),
            )
        return PairValue.from_tierkreis_pair(value)
    if inner_type := _extract_literal_type(type_):
        return TierkreisValue.from_python(value, inner_type)
    if inner_type := _is_annotated(type_):
        return TierkreisValue.from_python(value, inner_type)
    if union_args := _get_union_args(type_):
        for possible in union_args:
            # note if some possible type inherits from another possible type, an
            # instance of the child type may be converted as if it were an
            # instance of the parent (possibly losing some fields)
            try:
                with warnings.catch_warnings(record=True) as caught:
                    inner_val = TierkreisValue.from_python(value, possible)
                # Success, so issue warnings (perhaps to next catcher up)
                for w in caught:
                    warnings.warn(w.message, w.category)
                union_tag = UnionTag.type_tag(possible)
                return VariantValue(union_tag, inner_val)
            except IncompatiblePyValue:
                # Suppress (discard) warnings from failed variant
                continue
        raise IncompatiblePyValue(value)

    # base case try treating as class.
    _check_subclass(value, type_)
    return StructValue.from_object(value, type_)


def _check_subclass(value: Any, type_: typing.Type):
    value_type = type(value)
    if isinstance(type_, TypeVar):
        return  # skip check if type erased

    target_type = (
        # value_type could be GenericPydanticModel, list, NonGenericClass.
        # Compare against origin of type_, in case type_ is e.g. GenericPydanticModel[SomeArgs]
        (generic_origin(type_) or type_)
        if generic_origin(value_type) is None
        # value_type is GenericPydanticModel[SomeArgs] (it can never be e.g. list[Args])
        # So compare against exact type_, thus failing if type_ is GenericPydanticModel[DifferentArgs]
        else type_
    )

    if not issubclass(value_type, target_type):
        raise IncompatibleAnnotatedValue(value, type_)

    if value_type != target_type:
        warnings.warn(
            f"Ignoring extra fields in {value_type} beyond those in type {type_}."
        )
