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
    prefix = ", Generic" if in_constructor else ""
    return f"{prefix}[{', '.join(generics)}]" if generics else ""


def format_tmodel_type(outputs: type[PModel]) -> str:
    if is_portmapping(outputs):
        args = [str(x) for x in get_args(outputs)]
        return f"{outputs.__qualname__}{format_generics(args, False)}"

    return f"TKR[{format_ptype(outputs)}]"


def format_protocol_attribute(
    port_id: PortID, ptype: type[PType], is_constructor: bool = False
) -> str:
    return (
        f"@property\n    def {port_id}(self) -> {format_ptype(ptype)}: ... {NO_QA_STR}"
    )


def format_annotation(
    port_id: PortID, ptype: type[PType], is_constructor: bool = False
) -> str:
    sep = "=" if is_constructor else ":"
    constructor = f'(n, "{port_id}")' if is_constructor else ""
    return f"{port_id}{sep} TKR[{format_ptype(ptype)}]{constructor} {NO_QA_STR}"


def format_input_pnamedmodel(model: type[PNamedModel]) -> str:
    origin = get_origin(model)
    args = get_args(model)
    if origin is not None:
        model = origin

    outs = [format_protocol_attribute(k, v) for k, v in model.__annotations__.items()]
    outs.sort()
    outs_str = "\n    ".join(outs)

    generics = [str(x) for x in args]
    generics_str = f", Generic[{', '.join(generics)}]" if generics else ""

    return f"""
class {model.__qualname__}(Struct, Protocol{generics_str}):
    {outs_str}
"""


def format_input_pnamedmodels(models: set[type[PNamedModel]]) -> str:
    ms = sorted(list(models), key=lambda x: x.__name__)
    return "\n\n".join([format_input_pnamedmodel(x) for x in ms])


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
    return "\n".join([format_typevar(x) for x in sorted(list(generics))])


def format_output_pnamedmodel(pnamedmodel: type[PNamedModel]) -> str:
    origin = get_origin(pnamedmodel)
    args = get_args(pnamedmodel)
    if origin is not None:
        pnamedmodel = origin

    outs = [format_annotation(k, v) for k, v in pnamedmodel.__annotations__.items()]
    outs.sort()
    outs_str = "\n    ".join(outs)

    generics_str = format_generics([str(x) for x in args])

    return f"""
class {pnamedmodel.__qualname__}(NamedTuple{generics_str}):
    {outs_str}
"""


def format_output_pnamedmodels(models: set[type[PNamedModel]]) -> str:
    models_list = sorted(list(models), key=lambda x: x.__name__)
    return "\n\n".join([format_output_pnamedmodel(x) for x in models_list])


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

{format_input_pnamedmodels(namespace.input_models)}

{format_output_pnamedmodels(namespace.output_models)}

{functions_str}
    '''
