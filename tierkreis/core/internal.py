import inspect
import typing
from dataclasses import dataclass, fields, is_dataclass, replace
from typing import Any, Dict, ParamSpec, cast

from pydantic import BaseModel

from tierkreis.core.opaque_model import OpaqueModel


def substitute(
    type_: typing.Type, subst: Dict[typing.TypeVar, typing.Type]
) -> typing.Type:
    "Substitute type variables in a type."
    if isinstance(type_, typing.TypeVar):
        if type_ in subst:
            return subst[type_]
        else:
            return cast(typing.Type, type_)

    type_origin = typing.get_origin(type_)
    if type_origin is None:
        return type_
    else:
        return type_origin[  # type: ignore
            tuple([substitute(arg_type, subst) for arg_type in typing.get_args(type_)])
        ]


Out = tuple[typing.Type, str | None]


def _assert_annotation(annotation: typing.Type | None) -> typing.Type:
    if annotation is None:
        raise ValueError("Classes without type annotations cannot be converted.")

    return annotation


@dataclass(frozen=True)
class ClassField:
    """Capture required data about a class field."""

    name: str
    type_: typing.Type
    # the discriminant tag for the field, if it is a discriminated union
    discriminant: str | None
    # whether the field is present in the __init__ function
    init: bool = True
    default: Any = None


def python_struct_fields(
    type_: typing.Type | ParamSpec,
) -> list[ClassField]:
    """For a python dataclass or pydantic BaseModel"""
    type_origin = typing.get_origin(type_)
    if type_origin is not None:
        # Generic type
        type_subst = dict(zip(cast(Any, type_).__parameters__, typing.get_args(type_)))

        return [
            replace(field, type_=substitute(field.type_, type_subst))
            for field in python_struct_fields(type_origin)
        ]

    if inspect.isclass(type_) and issubclass(type_, BaseModel):
        import pydantic as pyd

        if issubclass(type_, OpaqueModel):
            model_type = cast(typing.Type[OpaqueModel], type_)

            return [
                ClassField(
                    model_type.tierkreis_field(),
                    str,
                    None,
                )
            ]
        model_type = cast(typing.Type[pyd.BaseModel], type_)
        model_fields = model_type.model_fields

        def _get_discriminator(f: pyd.fields.FieldInfo) -> str | None:
            disc = f.discriminator
            if isinstance(disc, pyd.Discriminator):
                raise ValueError("Discriminators must be static strings.")
            return disc

        return [
            ClassField(
                k,
                _assert_annotation(f.annotation),
                _get_discriminator(f),
                default=f.default,
            )
            for k, f in model_fields.items()
        ]
    if is_dataclass(type_):
        dat_fields = fields(type_)
        types = typing.get_type_hints(type_)
        return [
            ClassField(
                f.name,
                types[f.name],
                getattr(f.default, "discriminator", None),
                default=f.default,
            )
            for f in dat_fields
        ]

    raise ValueError("Can only convert dataclasses or pydantic BaseModel")
