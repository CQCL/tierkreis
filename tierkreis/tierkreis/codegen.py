from types import NoneType
from typing import assert_never, get_args, get_origin
from pydantic import BaseModel
from tierkreis.controller.data.core import PortID
from tierkreis.controller.data.models import (
    PModel,
    PNamedModel,
    generics_in_pmodel,
    is_pnamedmodel,
)
from tierkreis.controller.data.types import (
    DictConvertible,
    ListConvertible,
    PType,
    _is_generic,
    _is_list,
    _is_mapping,
    _is_tuple,
    _is_union,
)
from tierkreis.namespace import FunctionSpec, Namespace

NO_QA_STR = " # noqa: F821 # fmt: skip"


def format_ptype(ptype: type[PType]) -> str:
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
        return f"Sequence[{', '.join(args)}]"

    if _is_mapping(ptype):
        args = [format_ptype(x) for x in get_args(ptype)]
        return f"Mapping[{', '.join(args)}]"

    if issubclass(ptype, (bool, int, float, str, bytes, NoneType)):
        return ptype.__qualname__

    if issubclass(ptype, (DictConvertible, ListConvertible, BaseModel)):
        return f'OpaqueType["{ptype.__module__}.{ptype.__qualname__}"]'

    assert_never(ptype)


def format_generics(generics: set[str]) -> str:
    return f", Generic[{', '.join(generics)}]" if generics else ""


def format_tmodel_type(outputs: type[PModel]) -> str:
    if is_pnamedmodel(outputs):
        return str(outputs).split(".")[-1]

    return f"TKR[{format_ptype(outputs)}]"


def format_annotation(
    port_id: PortID, ptype: type[PType], is_constructor: bool = False
) -> str:
    sep = "=" if is_constructor else ":"
    constructor = f'(n, "{port_id}")' if is_constructor else ""
    return f"{port_id}{sep} {format_tmodel_type(ptype)}{constructor} {NO_QA_STR}"


def format_function(namespace_name: str, fn: FunctionSpec) -> str:
    ins = [format_annotation(k, v) for k, v in fn.ins.items()]
    ins_str = "\n    ".join(ins)
    class_name = format_tmodel_type(fn.outs)

    return f"""class {fn.name}(NamedTuple{format_generics(fn.generics)}):
    {ins_str}

    @staticmethod
    def out() -> type[{class_name}]:{NO_QA_STR}
        return {class_name}{NO_QA_STR}

    @property
    def namespace(self) -> str:
        return "{namespace_name}" """


def format_typevar(name: str) -> str:
    return f'{name} = TypeVar("{name}", bound=PType)'


def format_typevars(generics: set[str]) -> str:
    return "\n".join([format_typevar(x) for x in generics])


def format_pnamedmodel(pnamedmodel: type[PNamedModel]) -> str:
    origin = get_origin(pnamedmodel)
    if origin is not None:
        pnamedmodel = origin

    outs = {format_annotation(k, v) for k, v in pnamedmodel.__annotations__.items()}
    outs_str = "\n    ".join(outs)

    generics = generics_in_pmodel(pnamedmodel)
    generics_str = f", Generic[{", ".join(generics)}]" if generics else ""

    return f"""
class {pnamedmodel.__qualname__}(NamedTuple{generics_str}):
    {outs_str}
"""


def format_pnamedmodels(models: set[type[PNamedModel]]) -> str:
    return "\n\n".join([format_pnamedmodel(x) for x in models])


def format_namespace(namespace: Namespace) -> str:
    functions = [
        format_function(namespace.name, f) for f in namespace.functions.values()
    ]
    functions_str = "\n\n".join(functions)

    return f'''"""Code generated from {namespace.name} namespace. Please do not edit."""

from typing import Literal, NamedTuple, Sequence, TypeVar, Generic
from types import NoneType
from tierkreis.controller.data.models import TKR, OpaqueType
from tierkreis.controller.data.types import PType

{format_typevars(namespace.generics)}

{format_pnamedmodels(namespace.refs)}

{functions_str}
    '''
