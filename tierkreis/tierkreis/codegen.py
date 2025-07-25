from types import NoneType
from typing import assert_never, get_args, get_origin
from pydantic import BaseModel
from tierkreis.controller.data.core import PortID
from tierkreis.controller.data.models import PModel, PNamedModel, is_portmapping
from tierkreis.controller.data.types import (
    DictConvertible,
    ListConvertible,
    PType,
    Struct,
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
        return f"list[{', '.join(args)}]"

    if _is_mapping(ptype):
        args = [format_ptype(x) for x in get_args(ptype)]
        return f"dict[{', '.join(args)}]"

    if issubclass(ptype, (bool, int, float, str, bytes, NoneType, Struct)):
        return ptype.__qualname__

    if issubclass(ptype, (DictConvertible, ListConvertible, BaseModel)):
        return f'OpaqueType["{ptype.__module__}.{ptype.__qualname__}"]'

    assert_never(ptype)


def format_generics(generics: list[str], in_constructor: bool = True) -> str:
    prefix = "Generic" if in_constructor else ""
    return f"{prefix}[{', '.join(generics)}]" if generics else ""


def format_tmodel_type(outputs: type[PModel]) -> str:
    if is_portmapping(outputs):
        args = [str(x) for x in get_args(outputs)]
        return f"{outputs.__qualname__}{format_generics(args, False)}"

    return f"TKR[{format_ptype(outputs)}]"


def format_annotation(port_id: PortID, ptype: type[PType], is_raw: bool = False) -> str:
    t = format_ptype(ptype) if is_raw else f"TKR[{format_ptype(ptype)}]"
    return f"{port_id}: {t} {NO_QA_STR}"


def format_model(
    model: type[PNamedModel], bases: list[str], is_raw: bool = False
) -> str:
    origin = get_origin(model)
    args = get_args(model)
    if origin is not None:
        model = origin

    outs = [format_annotation(k, v, is_raw) for k, v in model.__annotations__.items()]
    outs.sort()
    outs_str = "\n    ".join(outs)

    if args:
        bases.append(format_generics([str(x) for x in args]))

    return f"""
class {model.__qualname__}({", ".join(bases)}):
    {outs_str}
"""


def format_function(namespace_name: str, fn: FunctionSpec) -> str:
    ins = [format_annotation(k, v) for k, v in fn.ins.items()]
    ins_str = "\n    ".join(ins)
    class_name = format_tmodel_type(fn.outs)

    bases = ["NamedTuple"]
    if fn.generics:
        bases.append(format_generics(fn.generics))

    return f"""class {fn.name}({", ".join(bases)}):
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
    return "\n".join([format_typevar(x) for x in sorted(list(generics))])


def format_input_models(models: set[type[PNamedModel]]) -> str:
    ms = sorted(list(models), key=lambda x: x.__name__)
    return "\n\n".join([format_model(x, ["Struct", "Protocol"], True) for x in ms])


def format_output_models(models: set[type[PNamedModel]]) -> str:
    ms = sorted(list(models), key=lambda x: x.__name__)
    return "\n\n".join([format_model(x, ["NamedTuple"]) for x in ms])


def format_namespace(namespace: Namespace) -> str:
    functions = [
        format_function(namespace.name, f) for f in namespace.functions.values()
    ]
    functions_str = "\n\n".join(functions)

    return f'''"""Code generated from {namespace.name} namespace. Please do not edit."""

from typing import Literal, NamedTuple, Sequence, TypeVar, Generic, Protocol
from types import NoneType
from tierkreis.controller.data.models import TKR, OpaqueType
from tierkreis.controller.data.types import PType, Struct

{format_typevars(namespace.generics)}

{format_input_models(namespace.input_models)}

{format_output_models(namespace.output_models)}

{functions_str}
    '''
