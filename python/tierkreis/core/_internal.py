# Utilities to extract fields from a class

import inspect
from dataclasses import dataclass, fields, is_dataclass
from typing import (
    Any,
    ParamSpec,
    Type,
    cast,
    get_origin,
    get_type_hints,
)

import pydantic as pyd

from tierkreis.core.opaque_model import OpaqueModel

Out = tuple[Type, str | None]


@dataclass(frozen=True)
class FieldExtractionError(Exception):
    """An error occurred while extracting fields from a class."""

    type_: Type | ParamSpec
    msg: str


def _assert_annotation(annotation: Type | None, struct_type: Type) -> Type:
    if annotation is None:
        raise FieldExtractionError(
            struct_type, "Classes without type annotations cannot be converted."
        )

    return annotation


@dataclass(frozen=True)
class ClassField:
    """Capture required data about a class field."""

    name: str
    type_: Type
    # the discriminant tag for the field, if it is a discriminated union
    discriminant: str | None
    # whether the field is present in the __init__ function
    init: bool = True
    default: Any = None


def python_struct_fields(
    type_: Type | ParamSpec,
) -> list[ClassField]:
    """For a python dataclass or pydantic BaseModel, extract the fields and their types."""
    if inspect.isclass(type_) and issubclass(type_, pyd.BaseModel):
        if issubclass(type_, OpaqueModel):
            model_type = cast(Type[OpaqueModel], type_)

            return [
                ClassField(
                    model_type.tierkreis_field(),
                    str,
                    None,
                )
            ]
        model_type = cast(Type[pyd.BaseModel], type_)
        model_fields = model_type.model_fields

        def _get_discriminator(f: pyd.fields.FieldInfo) -> str | None:
            disc = f.discriminator
            if isinstance(disc, pyd.Discriminator):
                raise ValueError("Discriminators must be static strings.")
            return disc

        return [
            ClassField(
                k,
                _assert_annotation(f.annotation, type_),
                _get_discriminator(f),
                default=f.default,
            )
            for k, f in model_fields.items()
        ]
    # pydantic binds concrete types to generic fields when available in the
    # annotation.
    # For generic dataclasses, just deal with the generic base type (used in workers).
    type_ = get_origin(type_) or type_
    if is_dataclass(type_):
        dat_fields = fields(type_)
        types = get_type_hints(type_)
        return [
            ClassField(
                f.name,
                types[f.name],
                getattr(f.default, "discriminator", None),
                default=f.default,
            )
            for f in dat_fields
        ]
    raise FieldExtractionError(
        type_, "Can only convert dataclasses or pydantic BaseModel."
    )


def generic_origin(type_: Type) -> Type | None:
    """Like typing.get_origin but also supports Generic pydantic 'BaseModel's"""
    if (o := get_origin(type_)) is not None:
        return o
    if inspect.isclass(type_) and issubclass(type_, pyd.BaseModel):
        # This taken from
        # https://github.com/pydantic/pydantic/blob/812516d71a8696d5e29c5bdab40336d82ccde412/pydantic/_internal/_generics.py#L214-L218
        pydantic_generic_metadata = getattr(
            type_, "__pydantic_generic_metadata__", None
        )
        if pydantic_generic_metadata:
            return pydantic_generic_metadata.get("origin")
        # BaseModel but not generic; fall through
    return None
