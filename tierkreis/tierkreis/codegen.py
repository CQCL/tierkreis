from types import NoneType
from typing import get_args, get_origin
from pydantic import BaseModel
from tierkreis.controller.data.types import (
    DictConvertible,
    ListConvertible,
    Struct,
    _is_generic,
    _is_list,
    _is_mapping,
    _is_tuple,
    _is_union,
)
from tierkreis.idl.models import GenericType, Method, Model, TypedArg
from tierkreis.namespace import Namespace

NO_QA_STR = " # noqa: F821 # fmt: skip"


def format_ptype(ptype: type) -> str:
    if isinstance(ptype, str):
        return ptype

    if _is_generic(ptype):
        return str(ptype)

    if _is_union(ptype):
        args = tuple([format_ptype(x) for x in get_args(ptype)])
        return " | ".join(args)

    if _is_tuple(ptype):
        args = [format_ptype(x) for x in get_args(ptype)]
        return f"tuple[{', '.join(args)}]"

    if _is_list(ptype):
        args = [format_ptype(x) for x in get_args(ptype)]
        return f"list[{', '.join(args)}]"

    if _is_mapping(ptype):
        args = [format_ptype(x) for x in get_args(ptype)]
        return f"dict[{', '.join(args)}]"

    origin = get_origin(ptype)
    if origin is not None:  # Custom generic
        args = [format_ptype(x) for x in get_args(ptype)]
        return f"{format_ptype(origin)}[{', '.join(args)}]"

    if issubclass(ptype, (bool, int, float, str, bytes, NoneType, Struct)):
        return ptype.__qualname__

    if issubclass(ptype, (DictConvertible, ListConvertible, BaseModel)):
        return f'OpaqueType["{ptype.__module__}.{ptype.__qualname__}"]'

    return ptype.__qualname__


def format_generic_type(
    generictype: GenericType | str, include_bound: bool, is_tkr: bool
) -> str:
    bound_str = ": PType" if include_bound else ""
    if isinstance(generictype, str):
        return generictype + bound_str

    if _is_generic(generictype):
        return str(generictype) + bound_str

    origin_str = (
        generictype.origin
        if isinstance(generictype.origin, str)
        else format_ptype(generictype.origin)
    )
    generics_str = (
        f"[{', '.join([format_generic_type(x, include_bound, False) for x in generictype.args])}]"
        if generictype.args
        else ""
    )

    if is_tkr:
        return f"TKR[{origin_str}{generics_str}]"

    return f"{origin_str}{generics_str}"


def format_typed_arg(typed_arg: TypedArg, is_portmaping: bool) -> str:
    return f"{typed_arg.name}: {format_generic_type(typed_arg.t, False, not is_portmaping)} {NO_QA_STR}"


def format_model(model: Model) -> str:
    is_portmapping = model.is_portmapping
    outs = [format_typed_arg(x, not is_portmapping) for x in model.decls]
    outs.sort()
    outs_str = "\n    ".join(outs)

    bases = ["NamedTuple"] if is_portmapping else ["Struct", "Protocol"]

    return f"""
class {format_generic_type(model.t, True, False)}({", ".join(bases)}):
    {outs_str}
"""


def format_method(namespace_name: str, fn: Method) -> str:
    ins = [format_typed_arg(x, False) for x in fn.args]
    ins_str = "\n    ".join(ins)
    class_name = format_generic_type(
        fn.return_type, False, not fn.return_type_is_portmapping
    )

    bases = ["NamedTuple"]

    return f"""class {format_generic_type(fn.name, True, False)}({", ".join(bases)}):
    {ins_str}

    @staticmethod
    def out() -> type[{class_name}]:{NO_QA_STR}
        return {class_name}{NO_QA_STR}

    @property
    def namespace(self) -> str:
        return "{namespace_name}" """


def format_namespace(namespace: Namespace) -> str:
    functions = [format_method(namespace.name, f) for f in namespace.methods]
    functions_str = "\n\n".join(functions)

    models = sorted(list(namespace.models), key=lambda x: str(x.t.origin))
    models_str = "\n\n".join([format_model(x) for x in models])

    return f'''"""Code generated from {namespace.name} namespace. Please do not edit."""

from typing import Literal, NamedTuple, Sequence, TypeVar, Generic, Protocol
from types import NoneType
from tierkreis.controller.data.models import TKR, OpaqueType
from tierkreis.controller.data.types import PType, Struct

{models_str}

{functions_str}
    '''
