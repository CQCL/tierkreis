from tierkreis.controller.data.core import PortID
from tierkreis.controller.data.types import _is_generic, format_ptype
from tierkreis.idl.models import ElementaryType, GenericType, Method, Model
from tierkreis.idl.python import generics_from_generictype
from tierkreis.namespace import Namespace

NO_QA_STR = " # noqa: F821 # fmt: skip"


def format_generics(generics: list[str], in_constructor: bool = True) -> str:
    prefix = "Generic" if in_constructor else ""
    return f"{prefix}[{', '.join(generics)}]" if generics else ""


def format_elementary_type(elementarytype: ElementaryType) -> str:
    if _is_generic(elementarytype):
        return str(elementarytype)

    if isinstance(elementarytype, str):
        return elementarytype

    return elementarytype.__qualname__


def format_generic_type(generictype: GenericType | str) -> str:
    if isinstance(generictype, str):
        return generictype

    origin_str = (
        generictype.origin
        if isinstance(generictype.origin, str)
        else format_ptype(generictype.origin)
    )
    generics_str = (
        "[" + ", ".join([format_generic_type(x) for x in generictype.args]) + "]"
        if generictype.args
        else ""
    )
    return f"{origin_str}{generics_str}"


def format_type(generic_type: GenericType, is_portmapping: bool) -> str:
    out = generic_type

    if is_portmapping:
        return f"{format_generic_type(out)}"

    return f"TKR[{format_generic_type(out)}]"


def format_annotation(port_id: PortID, ptype: GenericType, is_portmaping: bool) -> str:
    return f"{port_id}: {format_type(ptype, is_portmaping)} {NO_QA_STR}"


def format_model(model: Model) -> str:
    is_portmapping = model.is_portmapping
    outs = [format_annotation(x.name, x.t, not is_portmapping) for x in model.decls]
    outs.sort()
    outs_str = "\n    ".join(outs)

    bases = ["NamedTuple"] if is_portmapping else ["Struct", "Protocol"]
    if generics_from_generictype(model.t):
        bases.append(
            format_generics([str(x) for x in generics_from_generictype(model.t)])
        )

    return f"""
class {model.t.origin}({", ".join(bases)}):
    {outs_str}
"""


def format_method(namespace_name: str, fn: Method) -> str:
    ins = [format_annotation(x.name, x.t, False) for x in fn.args]
    ins_str = "\n    ".join(ins)
    class_name = format_type(fn.return_type, fn.return_type_is_portmapping)

    bases = ["NamedTuple"]
    if generics_from_generictype(fn.name):
        bases.append(format_generics(generics_from_generictype(fn.name)))

    return f"""class {fn.name.origin}({", ".join(bases)}):
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


def format_models(models: set[Model]) -> str:
    ms = sorted(list(models), key=lambda x: str(x.t.origin))
    return "\n\n".join([format_model(x) for x in ms])


def format_namespace(namespace: Namespace) -> str:
    functions = [format_method(namespace.name, f) for f in namespace.methods]
    functions_str = "\n\n".join(functions)

    return f'''"""Code generated from {namespace.name} namespace. Please do not edit."""

from typing import Literal, NamedTuple, Sequence, TypeVar, Generic, Protocol
from types import NoneType
from tierkreis.controller.data.models import TKR, OpaqueType
from tierkreis.controller.data.types import PType, Struct

{format_typevars(namespace.generics)}

{format_models(namespace.models)}

{functions_str}
    '''
