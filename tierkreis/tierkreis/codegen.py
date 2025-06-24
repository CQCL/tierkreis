import inspect
from typing import Any
from tierkreis.controller.data.core import PortID, TKRType
from tierkreis.namespace import FunctionSpec, Namespace


def format_type(tk_type: type[TKRType] | str) -> str:
    if isinstance(tk_type, str):
        return f'TKRRef[Literal["{tk_type}"]]'
    if inspect.isclass(tk_type):
        return f"TKRRef[{tk_type.__qualname__}]"
    return f"TKRRef[{tk_type}]"


def format_annotation(
    port_id: PortID, tk_type: type[TKRType] | str, is_constructor: bool = False
) -> str:
    sep = "=" if is_constructor else ":"
    constructor = f'(n, "{port_id}")' if is_constructor else ""
    return f"{port_id}{sep} {format_type(tk_type)}{constructor}"


def format_output(fn_name: str, outputs: dict[str, Any]) -> str:
    if len(outputs) == 1 and "value" in outputs:
        return format_type(outputs["value"])
    return f"{fn_name}Output"


def format_output_class(fn_name: str, outputs: dict[str, Any]) -> str:
    if len(outputs) == 1 and "value" in outputs:
        return ""

    outs = {format_annotation(k, v) for k, v in outputs.items()}
    outs_str = "\n    ".join(outs)

    out_constructor = {format_annotation(k, v, True) for k, v in outputs.items()}
    out_constructor_str = ",\n            ".join(out_constructor)
    return f"""
class {fn_name}Output(NamedTuple):
    {outs_str}

    @staticmethod
    def from_nodeindex(n: NodeIndex) -> "{fn_name}Output":
        return {fn_name}Output(
            {out_constructor_str}
        )

"""


def format_function(namespace_name: str, fn: FunctionSpec) -> str:
    ins = [format_annotation(k, v) for k, v in fn.ins.items()]
    ins_str = "\n    ".join(ins)
    class_name = format_output(fn.name, fn.outs)
    return f"""{format_output_class(fn.name, fn.outs)}
class {fn.name}(Function[{class_name}]):
    {ins_str}

    @staticmethod
    def out(idx: NodeIndex) -> {class_name}:
        return {class_name}.from_nodeindex(idx)

    @property
    def namespace(self) -> str:
        return "{namespace_name}" """


def format_namespace(namespace: Namespace) -> str:
    functions = [format_function(namespace.name, f) for f in namespace.functions]
    functions_str = "\n\n".join(functions)

    return f'''"""Code generated from {namespace.name} namespace. Please do not edit."""

from typing import Literal, NamedTuple
import typing
from tierkreis.controller.data.core import TKRRef, Function, NodeIndex

{functions_str}
    '''
