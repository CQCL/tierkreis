import typing
from typing import cast, Any


def python_struct_fields(type_: typing.Type) -> dict[str, typing.Type]:
    def substitute(
        type_: typing.Type, subst: dict[typing.TypeVar, typing.Type]
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
            return type_origin[
                tuple(
                    [substitute(arg_type, subst) for arg_type in typing.get_args(type_)]
                )
            ]

    if typing.get_origin(type_) is None:
        # Non generic type
        return typing.get_type_hints(type_)
    else:
        # Generic type
        type_origin = typing.get_origin(type_)
        type_subst = dict(zip(cast(Any, type_).__parameters__, typing.get_args(type_)))

        return {
            field_name: substitute(field_type, type_subst)
            for field_name, field_type in typing.get_type_hints(type_origin).items()
        }
