from typing import Any
from tierkreis.controller.data.core import PortID, TKType
from tierkreis.namespace import FunctionSpec, Namespace


def format_type(tk_type: TKType) -> str:
    if isinstance(tk_type, str):
        return f"TypedValueRef[Literal[{tk_type}]]"
    return f"TypedValueRef[{tk_type.__qualname__}]"


def format_annotation(
    port_id: PortID, tk_type: TKType, is_constructor: bool = False
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
class {fn_name}Output(BaseModel):
    {outs_str}

    @staticmethod
    def from_valueref(ref: ValueRef) -> "{fn_name}Output":
        n = ref[0]
        return {fn_name}Output(
            {out_constructor_str}
        )

"""


def format_function(fn: FunctionSpec) -> str:
    ins = [format_annotation(k, v) for k, v in fn.ins.items()]
    ins_str = "\n    ".join(ins)
    class_name = format_output(fn.name, fn.outs)
    return f"""{format_output_class(fn.name, fn.outs)}
class {fn.name}(Function[{class_name}]):
    {ins_str}

    out: Callable[[ValueRef], {class_name}] = {class_name}.from_valueref"""


def format_namespace(namespace: Namespace) -> str:
    functions = [format_function(f) for f in namespace.functions]
    functions_str = "\n\n".join(functions)

    return f'''"""Code generated from {namespace.name} namspace. Please do not edit."""

from typing import Callable
from pydantic import BaseModel
from tierkreis.controller.data.core import TypedValueRef, Function, ValueRef

{functions_str}
    '''
