from typing import ForwardRef
from tierkreis.controller.data.core import PortID
from tierkreis.idl.models import GenericType, Method, Model
from tierkreis.namespace import Namespace

NO_QA_STR = " # noqa: F821 # fmt: skip"


def format_generics(generics: list[str], in_constructor: bool = True) -> str:
    prefix = "Generic" if in_constructor else ""
    return f"{prefix}[{', '.join(generics)}]" if generics else ""


def format_type(generic_type: GenericType, is_portmapping: bool) -> str:
    out = generic_type.t

    if isinstance(out, ForwardRef):
        out = out.__forward_arg__

    if is_portmapping:
        return f"{out}{format_generics(generic_type.generics, False)}"

    return f"TKR[{out}{format_generics(generic_type.generics, False)}]"


def format_annotation(port_id: PortID, ptype: GenericType, is_portmaping: bool) -> str:
    return f"{port_id}: {format_type(ptype, is_portmaping)} {NO_QA_STR}"


def format_model(model: Model) -> str:
    is_portmapping = model.is_portmapping
    outs = [format_annotation(x.name, x.t, not is_portmapping) for x in model.decls]
    outs.sort()
    outs_str = "\n    ".join(outs)

    bases = ["NamedTuple"] if is_portmapping else ["Struct", "Protocol"]
    if model.generics:
        bases.append(format_generics([str(x) for x in model.generics]))

    return f"""
class {model.name}({", ".join(bases)}):
    {outs_str}
"""


def format_method(namespace_name: str, fn: Method) -> str:
    ins = [format_annotation(x.name, x.t, False) for x in fn.args]
    ins_str = "\n    ".join(ins)
    class_name = format_type(fn.return_type, fn.return_type_is_portmapping)

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


def format_models(models: set[Model]) -> str:
    ms = sorted(list(models), key=lambda x: x.name)
    return "\n\n".join([format_model(x) for x in ms])


def format_namespace(namespace: Namespace) -> str:
    functions = [format_method(namespace.name, f) for f in namespace.methods.values()]
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
