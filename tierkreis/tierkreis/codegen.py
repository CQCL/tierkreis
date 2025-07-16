from types import NoneType
from typing import assert_never, get_args, get_origin
from pydantic import BaseModel
from tierkreis.controller.data.core import PortID
from tierkreis.controller.data.models import PModel, generics_in_pmodel, is_pnamedmodel
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


def format_generics(generics: set[str], include_ptype: bool = True) -> str:
    ptype_annotation = ": PType" if include_ptype else ""
    generics_strs = [str(x) + ptype_annotation for x in generics]
    return f"[{', '.join(generics_strs)}]" if generics else ""


def format_annotation(
    port_id: PortID, ptype: type[PType], is_constructor: bool = False
) -> str:
    sep = "=" if is_constructor else ":"
    constructor = f'(n, "{port_id}")' if is_constructor else ""
    return f"{port_id}{sep} TKR[{format_ptype(ptype)}]{constructor} {NO_QA_STR}"


def format_output(outputs: type[PModel], include_ptype: bool = True) -> str:
    generics = format_generics(generics_in_pmodel(outputs), include_ptype)
    if is_pnamedmodel(outputs):
        return f"{outputs.__qualname__}{generics}"

    return f"TKR[{format_ptype(outputs)}]"


def format_output_class(outputs: type[PModel]) -> str:
    class_name = format_output(outputs)
    if not is_pnamedmodel(outputs):
        return ""

    origin = get_origin(outputs)
    if origin is not None:
        outputs = origin

    outs = {format_annotation(k, v) for k, v in outputs.__annotations__.items()}
    outs_str = "\n    ".join(outs)

    return f"""
class {class_name}(NamedTuple):
    {outs_str}
"""


def format_function(namespace_name: str, fn: FunctionSpec) -> str:
    ins = [format_annotation(k, v) for k, v in fn.ins.items()]
    ins_str = "\n    ".join(ins)
    class_name = format_output(fn.outs, False)

    return f"""{format_output_class(fn.outs)}
class {fn.name}{format_generics(fn.generics)}(NamedTuple):
    {ins_str}

    @staticmethod
    def out() -> type[{class_name}]:{NO_QA_STR}
        return {class_name}{NO_QA_STR}

    @property
    def namespace(self) -> str:
        return "{namespace_name}" """


def format_namespace(namespace: Namespace) -> str:
    functions = [
        format_function(namespace.name, f) for f in namespace.functions.values()
    ]
    functions_str = "\n\n".join(functions)

    return f'''"""Code generated from {namespace.name} namespace. Please do not edit."""

from typing import Literal, NamedTuple, Sequence
from types import NoneType
from tierkreis.controller.data.models import TKR, OpaqueType
from tierkreis.controller.data.types import PType

{functions_str}
    '''
