from typing import get_args, get_origin
from tierkreis.controller.data.types import _is_generic
from tierkreis.exceptions import TierkreisError
from tierkreis.idl.models import GenericType


def generictype_from_type(t: type) -> GenericType:
    args, origin = get_args(t), get_origin(t)
    if not args:
        return GenericType(t, [])

    if args and origin:
        subargs = []
        for arg in args:
            if isinstance(arg, str):
                subargs.append(arg)
            else:
                subargs.append(generictype_from_type(arg))

        return GenericType(origin, subargs)

    raise TierkreisError(f"Expected generic type. Got {t}")


def generics_from_generictype(generictype: GenericType | str) -> list[str]:
    if _is_generic(generictype):
        return str(generictype)

    if isinstance(generictype, str):
        return [generictype]

    if generictype.args == []:
        return []

    outs = []
    for arg in generictype.args:
        outs.extend(generics_from_generictype(arg))
    return outs
