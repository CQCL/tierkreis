from inspect import isclass
from tierkreis.controller.data.core import PortID
from tierkreis.controller.data.models import PModel, PNamedModel
from tierkreis.controller.data.types import PType, format_ptype
from tierkreis.namespace import FunctionSpec, Namespace


def format_annotation(
    port_id: PortID, ptype: type[PType], is_constructor: bool = False
) -> str:
    sep = "=" if is_constructor else ":"
    constructor = f'(n, "{port_id}")' if is_constructor else ""
    return f"{port_id}{sep} TKR[{format_ptype(ptype)}]{constructor} # noqa: F821 # fmt: skip"


def format_output(outputs: type[PModel]) -> str:
    if isclass(outputs) and issubclass(outputs, PNamedModel):
        return outputs.__qualname__

    return f"TKR[{format_ptype(outputs)}]"


def format_output_class(fn_name: str, class_name: str, outputs: type[PModel]) -> str:
    if not isclass(outputs) or not issubclass(outputs, PNamedModel):
        return ""

    outs = {format_annotation(k, v) for k, v in outputs.__annotations__.items()}
    outs_str = "\n    ".join(outs)

    return f"""
class {class_name}(NamedTuple):
    {outs_str}
"""


def format_function(namespace_name: str, fn: FunctionSpec) -> str:
    ins = [format_annotation(k, v) for k, v in fn.ins.items()]
    ins_str = "\n    ".join(ins)
    class_name = format_output(fn.outs)
    return f"""{format_output_class(fn.name, class_name, fn.outs)}
class {fn.name}(NamedTuple):
    {ins_str}

    @staticmethod
    def out() -> type[{class_name}]: # noqa: F821 # fmt: skip
        return {class_name} # noqa: F821 # fmt: skip

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
import typing
from tierkreis.controller.data.models import TKR, OpaqueType

{functions_str}
    '''
