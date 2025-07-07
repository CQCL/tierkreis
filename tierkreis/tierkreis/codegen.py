from typing import NamedTuple
from tierkreis.controller.data.core import PortID
from tierkreis.controller.data.models import PModel, PNamedModel
from tierkreis.controller.data.types import PType, format_ttype, ttype_from_ptype
from tierkreis.namespace import FunctionSpec, Namespace


def format_annotation(
    port_id: PortID, ptype: type[PType], is_constructor: bool = False
) -> str:
    sep = "=" if is_constructor else ":"
    constructor = f'(n, "{port_id}")' if is_constructor else ""
    ttype = ttype_from_ptype(ptype)
    return f"{port_id}{sep} {format_ttype(ttype)}{constructor}"


def format_output(outputs: type[PModel]) -> str:
    if issubclass(outputs, PNamedModel):
        return outputs.__qualname__

    return format_ttype(ttype_from_ptype(outputs))


def format_output_class(fn_name: str, outputs: type[PModel]) -> str:
    if not issubclass(outputs, PNamedModel):
        return ""

    outs = {format_annotation(k, v) for k, v in outputs.__annotations__.items()}
    outs_str = "\n    ".join(outs)

    out_constructor = {
        format_annotation(k, v, True) for k, v in outputs.__annotations__.items()
    }
    out_constructor_str = ",\n            ".join(out_constructor)
    return f"""
class {fn_name.title()}Output(NamedTuple):
    {outs_str}

    @staticmethod
    def from_nodeindex(n: NodeIndex) -> "{fn_name.title()}Output":
        return {fn_name.title()}Output(
            {out_constructor_str}
        )

"""


def format_function(namespace_name: str, fn: FunctionSpec) -> str:
    ins = [format_annotation(k, v) for k, v in fn.ins.items()]
    ins_str = "\n    ".join(ins)
    class_name = format_output(fn.outs)
    return f"""{format_output_class(fn.name, fn.outs)}
class {fn.name}(NamedTuple):
    {ins_str}

    @staticmethod
    def out() -> type:
        return {class_name}

    @property
    def namespace(self) -> str:
        return "{namespace_name}" """


def format_namespace(namespace: Namespace) -> str:
    functions = [
        format_function(namespace.name, f) for f in namespace.functions.values()
    ]
    functions_str = "\n\n".join(functions)

    return f'''"""Code generated from {namespace.name} namespace. Please do not edit."""

from typing import Literal, NamedTuple
import typing
from tierkreis.controller.data.types import TBool, TInt, TFloat, TStr, TNone, TBytes, TList, TTuple

{functions_str}
    '''
